"""Load Federal Register notices and extracted HTS links into Snowflake."""

import logging
from typing import Any, Dict, List, Sequence

logger = logging.getLogger(__name__)

NOTICE_BATCH = 100
HTS_BATCH = 500

DDL_NOTICES = """
CREATE TABLE IF NOT EXISTS FEDERAL_REGISTER_NOTICES (
    DOCUMENT_NUMBER     VARCHAR(50)     PRIMARY KEY,
    TITLE               VARCHAR(1000),
    PUBLICATION_DATE    DATE,
    DOCUMENT_TYPE       VARCHAR(50),
    AGENCY_NAMES        VARCHAR(500),
    ABSTRACT            VARCHAR(2000),
    FULL_TEXT           TEXT,
    HTML_URL            VARCHAR(500),
    BODY_HTML_URL       VARCHAR(500),
    CHAR_COUNT          NUMBER,
    CHUNK_COUNT         NUMBER,
    RAW_JSON            VARIANT,
    INGESTED_AT         TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP()
)
"""

DDL_NOTICE_HTS = """
CREATE TABLE IF NOT EXISTS NOTICE_HTS_CODES (
    DOCUMENT_NUMBER     VARCHAR(50)     REFERENCES FEDERAL_REGISTER_NOTICES (DOCUMENT_NUMBER),
    HTS_CODE            VARCHAR(20),
    HTS_CHAPTER         NUMBER(2),
    CONTEXT_SNIPPET     VARCHAR(500),
    PRIMARY KEY (DOCUMENT_NUMBER, HTS_CODE)
)
"""

INSERT_NOTICE_SQL = """
INSERT INTO FEDERAL_REGISTER_NOTICES (
    DOCUMENT_NUMBER,
    TITLE,
    PUBLICATION_DATE,
    DOCUMENT_TYPE,
    AGENCY_NAMES,
    ABSTRACT,
    FULL_TEXT,
    HTML_URL,
    BODY_HTML_URL,
    CHAR_COUNT,
    CHUNK_COUNT,
    RAW_JSON
)
SELECT
    v.c1,
    v.c2,
    v.c3,
    v.c4,
    v.c5,
    v.c6,
    v.c7,
    v.c8,
    v.c9,
    v.c10,
    v.c11,
    PARSE_JSON(v.c12)
FROM (VALUES {values_clause}) AS v(
    c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12
)
WHERE NOT EXISTS (
    SELECT 1 FROM FEDERAL_REGISTER_NOTICES n WHERE n.DOCUMENT_NUMBER = v.c1
)
"""

INSERT_HTS_SQL = """
INSERT INTO NOTICE_HTS_CODES (
    DOCUMENT_NUMBER,
    HTS_CODE,
    HTS_CHAPTER,
    CONTEXT_SNIPPET
)
SELECT v.c1, v.c2, v.c3, v.c4
FROM (VALUES {values_clause}) AS v(c1, c2, c3, c4)
WHERE NOT EXISTS (
    SELECT 1 FROM NOTICE_HTS_CODES x
    WHERE x.DOCUMENT_NUMBER = v.c1 AND x.HTS_CODE = v.c2
)
"""


def ensure_tables(conn: Any) -> None:
    """Create Source 2 tables if they do not exist."""
    with conn.cursor() as cur:
        cur.execute(DDL_NOTICES)
        cur.execute(DDL_NOTICE_HTS)
    logger.info("Ensured FEDERAL_REGISTER_NOTICES and NOTICE_HTS_CODES exist")


def _notice_values_clause(n: int) -> str:
    return ", ".join(n * ["(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"])


def _flatten_notice_batch(batch: Sequence[Dict[str, Any]]) -> List[Any]:
    flat: List[Any] = []
    for row in batch:
        flat.extend(
            [
                row["DOCUMENT_NUMBER"],
                row["TITLE"],
                row["PUBLICATION_DATE"],
                row["DOCUMENT_TYPE"],
                row["AGENCY_NAMES"],
                row["ABSTRACT"],
                row["FULL_TEXT"],
                row["HTML_URL"],
                row["BODY_HTML_URL"],
                row["CHAR_COUNT"],
                row["CHUNK_COUNT"],
                row["RAW_JSON"],
            ]
        )
    return flat


def load_notices(records: List[Dict[str, Any]], conn: Any) -> int:
    """Idempotent batch insert into FEDERAL_REGISTER_NOTICES (skip existing DOCUMENT_NUMBER)."""
    ensure_tables(conn)
    total = 0
    with conn.cursor() as cur:
        for i in range(0, len(records), NOTICE_BATCH):
            batch = records[i : i + NOTICE_BATCH]
            n = len(batch)
            if n == 0:
                continue
            sql = INSERT_NOTICE_SQL.format(values_clause=_notice_values_clause(n))
            cur.execute(sql, _flatten_notice_batch(batch))
            total += cur.rowcount or 0
            logger.info(
                "Notices batch %s–%s inserted (rowcount=%s)",
                i + 1,
                i + n,
                cur.rowcount,
            )
    logger.info("load_notices completed; rows inserted this run: %s", total)
    return total


def _hts_values_clause(n: int) -> str:
    return ", ".join(n * ["(%s, %s, %s, %s)"])


def _flatten_hts_batch(batch: Sequence[Dict[str, Any]]) -> List[Any]:
    flat: List[Any] = []
    for row in batch:
        flat.extend(
            [
                row["DOCUMENT_NUMBER"],
                row["HTS_CODE"],
                row["HTS_CHAPTER"],
                row["CONTEXT_SNIPPET"],
            ]
        )
    return flat


def load_hts_codes(hts_records: List[Dict[str, Any]], conn: Any) -> int:
    """Idempotent batch insert into NOTICE_HTS_CODES."""
    ensure_tables(conn)
    total = 0
    with conn.cursor() as cur:
        for i in range(0, len(hts_records), HTS_BATCH):
            batch = hts_records[i : i + HTS_BATCH]
            n = len(batch)
            if n == 0:
                continue
            sql = INSERT_HTS_SQL.format(values_clause=_hts_values_clause(n))
            cur.execute(sql, _flatten_hts_batch(batch))
            total += cur.rowcount or 0
            logger.info(
                "Notice HTS batch %s–%s inserted (rowcount=%s)",
                i + 1,
                i + n,
                cur.rowcount,
            )
    logger.info("load_hts_codes completed; rows inserted this run: %s", total)
    return total
