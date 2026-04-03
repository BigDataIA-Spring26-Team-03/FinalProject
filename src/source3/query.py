"""Snowflake queries joining Source 1 (HTS) and Source 2 (Federal Register) for Source 3 demos."""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

HTS_INFO_SQL = """
SELECT
    HTS_CODE,
    DESCRIPTION,
    LEVEL,
    GENERAL_RATE,
    SPECIAL_RATE,
    OTHER_RATE,
    CHAPTER,
    SECTION_NUMBER
FROM HTS_CODES
WHERE HTS_CODE LIKE %s
  AND LEVEL IN ('subheading', 'statistical')
  AND IS_HEADER_ROW = FALSE
  AND HTS_CODE IS NOT NULL
ORDER BY HTS_CODE ASC
LIMIT 10
"""

POLICY_DOCS_SQL = """
SELECT
    n.DOCUMENT_NUMBER,
    n.TITLE,
    n.PUBLICATION_DATE,
    n.HTML_URL,
    h.HTS_CODE,
    h.CONTEXT_SNIPPET
FROM FEDERAL_REGISTER_NOTICES n
JOIN NOTICE_HTS_CODES h
    ON n.DOCUMENT_NUMBER = h.DOCUMENT_NUMBER
WHERE h.HTS_CODE LIKE %s
ORDER BY n.PUBLICATION_DATE DESC
LIMIT 10
"""


def _rows_to_dicts(cur: Any) -> List[Dict[str, Any]]:
    columns = [c[0] for c in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]


def get_hts_info(conn: Any, hts_prefix: str) -> List[Dict[str, Any]]:
    pattern = hts_prefix + "%"
    with conn.cursor() as cur:
        cur.execute(HTS_INFO_SQL, (pattern,))
        rows = _rows_to_dicts(cur)
    logger.info("get_hts_info returned %s rows for prefix %s", len(rows), hts_prefix)
    return rows


def get_policy_docs(conn: Any, hts_prefix: str) -> List[Dict[str, Any]]:
    pattern = hts_prefix + "%"
    with conn.cursor() as cur:
        cur.execute(POLICY_DOCS_SQL, (pattern,))
        rows = _rows_to_dicts(cur)
    logger.info("get_policy_docs returned %s rows for prefix %s", len(rows), hts_prefix)
    return rows
