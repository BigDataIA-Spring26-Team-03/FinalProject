"""Extract HTS-like codes from plain text and match Source 1 Snowflake rows."""

import logging
import re
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)

HTS_PATTERN = re.compile(r"\b\d{4}\.\d{2}(?:\.\d{2,4})?\b")


def _sentence_for_match(text: str, start: int, end: int) -> str:
    """
    Approximate the sentence containing [start:end] using newlines or `.` boundaries
    without splitting inside the matched HTS token.
    """
    left = text.rfind("\n", 0, start)
    if left == -1:
        left = 0
    else:
        left += 1

    prev_dot = text.rfind(".", 0, start)
    if prev_dot != -1 and prev_dot >= left:
        after_dot = text[prev_dot + 1 : start]
        if after_dot.strip() == "" or (after_dot.startswith(" ") and "\n" not in after_dot):
            left = prev_dot + 1
        elif text[prev_dot : prev_dot + 2] == ". ":
            left = prev_dot + 2

    right_nl = text.find("\n", end)
    if right_nl == -1:
        right_nl = len(text)

    right_dot = text.find(".", end)
    while right_dot != -1 and right_dot < right_nl:
        nxt = right_dot + 1
        if nxt < len(text) and text[nxt] == ".":
            break
        if right_dot + 1 < len(text) and text[right_dot + 1].isspace():
            right_nl = min(right_nl, right_dot + 1)
            break
        right_dot = text.find(".", right_dot + 1)

    snippet = text[left:right_nl].strip()
    return snippet[:500] if snippet else text[max(0, start - 200) : end + 200].strip()[:500]


def _hts_chapter(code: str) -> int:
    digits = re.sub(r"[^\d]", "", code)
    if len(digits) < 2:
        return int(digits) if digits else 0
    return int(digits[:2])


def extract_hts_codes(document_number: str, clean_text: str) -> List[Dict[str, Any]]:
    """
    Find HTS-like codes in plain text, attach a short context snippet per first occurrence.
    """
    if not clean_text:
        return []

    seen: Set[str] = set()
    out: List[Dict[str, Any]] = []

    for m in HTS_PATTERN.finditer(clean_text):
        code = m.group(0)
        if code in seen:
            continue
        seen.add(code)
        snippet = _sentence_for_match(clean_text, m.start(), m.end())
        out.append(
            {
                "DOCUMENT_NUMBER": document_number,
                "HTS_CODE": code,
                "HTS_CHAPTER": _hts_chapter(code),
                "CONTEXT_SNIPPET": snippet[:500],
            }
        )
    return out


def match_to_source1(
    hts_codes: List[Dict[str, Any]],
    snowflake_conn: Any,
) -> Dict[str, Dict[str, Any]]:
    """
    Look up extracted codes in Source 1 HTS_CODES. Returns map:
    HTS_CODE -> {description, general_rate}
    """
    if not hts_codes:
        logger.info("Source 1 match: 0 codes to resolve (empty extraction)")
        return {}

    unique = []
    seen: Set[str] = set()
    for row in hts_codes:
        c = row.get("HTS_CODE")
        if c and c not in seen:
            seen.add(c)
            unique.append(c)

    if not unique:
        return {}

    cursor = snowflake_conn.cursor()
    try:
        result: Dict[str, Dict[str, Any]] = {}
        chunk_size = 200
        for i in range(0, len(unique), chunk_size):
            chunk = unique[i : i + chunk_size]
            placeholders = ", ".join(["%s"] * len(chunk))
            sql = f"""
                SELECT h.HTS_CODE, h.DESCRIPTION, h.GENERAL_RATE
                FROM HTS_CODES h
                WHERE h.HTS_CODE IN ({placeholders})
                  AND h.HTS_CODE IS NOT NULL
            """
            cursor.execute(sql, chunk)
            for code, desc, gen in cursor.fetchall():
                result[str(code)] = {
                    "description": desc,
                    "general_rate": gen,
                }
    finally:
        cursor.close()

    logger.info(
        "Source 1 match: %s of %s unique extracted codes matched HTS_CODES",
        len(result),
        len(unique),
    )
    return result
