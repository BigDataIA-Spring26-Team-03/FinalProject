"""Federal Register (Source 2) POC: fetch USTR tariff notices, extract HTS codes, load Snowflake."""

import logging
import sys
from typing import Any, Dict, List

import snowflake.connector
from tabulate import tabulate

from config import settings
from src.source2.extract_hts import extract_hts_codes, match_to_source1
from src.source2.fetch import fetch_documents, fetch_full_text
from src.source2.load import load_hts_codes, load_notices
from src.source2.parse import clean_html, parse_document

LOG_FORMAT = "%(asctime)s — %(levelname)s — %(message)s"

DEMO_SQL = """
SELECT
    n.DOCUMENT_NUMBER,
    n.TITLE,
    n.PUBLICATION_DATE,
    h.HTS_CODE,
    c.DESCRIPTION,
    c.GENERAL_RATE,
    h.CONTEXT_SNIPPET
FROM FEDERAL_REGISTER_NOTICES n
JOIN NOTICE_HTS_CODES h ON n.DOCUMENT_NUMBER = h.DOCUMENT_NUMBER
JOIN HTS_CODES c ON h.HTS_CODE = c.HTS_CODE
WHERE h.HTS_CODE LIKE '8471%'
ORDER BY n.PUBLICATION_DATE DESC
LIMIT 10
"""


def _build_notice_row(parsed: Dict[str, Any], full_text: Any, char_count: Any, chunk_count: int) -> Dict[str, Any]:
    return {
        "DOCUMENT_NUMBER": str(parsed["DOCUMENT_NUMBER"]),
        "TITLE": parsed["TITLE"],
        "PUBLICATION_DATE": parsed["PUBLICATION_DATE"],
        "DOCUMENT_TYPE": parsed["DOCUMENT_TYPE"],
        "AGENCY_NAMES": parsed["AGENCY_NAMES"],
        "ABSTRACT": parsed["ABSTRACT"],
        "FULL_TEXT": full_text,
        "HTML_URL": parsed["HTML_URL"],
        "BODY_HTML_URL": parsed["BODY_HTML_URL"],
        "CHAR_COUNT": char_count,
        "CHUNK_COUNT": chunk_count,
        "RAW_JSON": parsed["RAW_JSON"],
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    logger = logging.getLogger(__name__)

    notice_rows: List[Dict[str, Any]] = []
    all_hts_rows: List[Dict[str, Any]] = []
    total_extracted = 0
    total_matched = 0

    try:
        logger.info("Source 2 pipeline started")

        raw_docs = fetch_documents()
        logger.info("Step 1 complete: %s documents fetched", len(raw_docs))

        try:
            conn = snowflake.connector.connect(
                user=settings.SNOWFLAKE_USER,
                password=settings.SNOWFLAKE_PASSWORD,
                account=settings.SNOWFLAKE_ACCOUNT,
                warehouse=settings.SNOWFLAKE_WAREHOUSE,
                database=settings.SNOWFLAKE_DATABASE,
                schema=settings.SNOWFLAKE_SCHEMA,
            )
        except Exception as exc:
            print(f"Snowflake connection failed: {exc}", file=sys.stderr)
            raise

        try:
            for raw in raw_docs:
                parsed = parse_document(raw)
                doc_no = parsed.get("DOCUMENT_NUMBER")
                if not doc_no:
                    logger.warning("Skipping document with missing document_number")
                    continue

                body_url = parsed.get("BODY_HTML_URL")
                raw_html = None
                if not body_url:
                    logger.warning(
                        "Missing body_html_url for document %s; skipping full text fetch",
                        doc_no,
                    )
                else:
                    try:
                        raw_html = fetch_full_text(body_url)
                    except Exception as exc:
                        logger.warning(
                            "Full text fetch failed for %s: %s — storing NULL FULL_TEXT",
                            doc_no,
                            exc,
                        )

                clean_text = None
                if raw_html is not None:
                    try:
                        clean_text = clean_html(raw_html)
                    except Exception as exc:
                        logger.error(
                            "BeautifulSoup failed for document %s: %s — skipping this document",
                            doc_no,
                            exc,
                        )
                        continue

                if clean_text:
                    char_count = len(clean_text)
                    chunk_count = 1
                else:
                    char_count = None
                    chunk_count = 0

                notice_rows.append(
                    _build_notice_row(parsed, clean_text, char_count, chunk_count)
                )

                extracted = extract_hts_codes(str(doc_no), clean_text or "")
                total_extracted += len(extracted)
                matches = match_to_source1(extracted, conn)
                total_matched += sum(1 for r in extracted if r["HTS_CODE"] in matches)
                all_hts_rows.extend(extracted)

            logger.info("Step 2–3 complete: parsed %s notices; extracted %s HTS mentions", len(notice_rows), total_extracted)

            loaded_notices = load_notices(notice_rows, conn)
            loaded_hts = load_hts_codes(all_hts_rows, conn)
            conn.commit()
            logger.info("Step 4 complete: Snowflake load committed")

            with conn.cursor() as cur:
                cur.execute(DEMO_SQL)
                columns = [col[0] for col in cur.description]
                demo_rows = cur.fetchall()

            print()
            print("DEMO QUERY — Laptop/Computer tariff documents cross-referenced with Source 1")
            print()
            print(tabulate(demo_rows, headers=columns, tablefmt="pretty"))
            print()

        finally:
            conn.close()

        logger.info("Source 2 pipeline finished successfully")

        print("Summary")
        print("-------")
        print(f"  Total documents fetched:     {len(raw_docs)}")
        print(f"  Total notices loaded (new):    {loaded_notices}")
        print(f"  Total HTS rows loaded (new):   {loaded_hts}")
        print(f"  Total HTS codes extracted:     {total_extracted}")
        print(f"  Total matched to Source 1:     {total_matched}")
        print()

    except Exception as exc:
        logger.exception("Source 2 pipeline failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
