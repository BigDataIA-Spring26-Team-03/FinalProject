"""Parse raw USITC export rows into Snowflake-shaped records."""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_NON_DIGIT = re.compile(r"[^\d]")

# HTS section number by chapter (1–99).
CHAPTER_TO_SECTION: Dict[int, int] = {}
for ch, sec in [
    (range(1, 6), 1),
    (range(6, 15), 2),
    (range(15, 16), 3),
    (range(16, 25), 4),
    (range(25, 28), 5),
    (range(28, 39), 6),
    (range(39, 41), 7),
    (range(41, 44), 8),
    (range(44, 47), 9),
    (range(47, 50), 10),
    (range(50, 64), 11),
    (range(64, 68), 12),
    (range(68, 71), 13),
    (range(71, 72), 14),
    (range(72, 84), 15),
    (range(84, 86), 16),
    (range(86, 90), 17),
    (range(90, 93), 18),
    (range(93, 94), 19),
    (range(94, 97), 20),
    (range(97, 100), 21),
]:
    for c in ch:
        CHAPTER_TO_SECTION[c] = sec


def _section_number(chapter: Optional[int]) -> Optional[int]:
    if chapter is None:
        return None
    return CHAPTER_TO_SECTION.get(chapter)


def _hts_level(hts_code: Optional[str]) -> str:
    """Classify hierarchy from dot structure; header rows use a dedicated level."""
    if hts_code is None:
        return "header"
    stripped = hts_code.strip()
    if not stripped:
        return "header"
    dot_count = stripped.count(".")
    if dot_count == 0:
        if len(stripped) <= 2:
            return "chapter"
        return "heading"
    if dot_count == 1:
        return "subheading"
    return "statistical"


def _chapter_number(hts_code: Optional[str]) -> Optional[int]:
    """Two-digit chapter from the HTS number (digits only, first two positions)."""
    if hts_code is None:
        return None
    stripped = hts_code.strip()
    if not stripped:
        return None
    digits = _NON_DIGIT.sub("", stripped)
    if len(digits) < 2:
        return int(digits) if digits else None
    return int(digits[:2])


def _split_hts_and_stat_suffix(htsno: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Split API `htsno` into 8-digit-style HTS_CODE and 2-digit STAT_SUFFIX.

    Examples: ``8471.30.01.00`` → ``8471.30.01``, ``00``;
    ``8471.30.0100`` → ``8471.30.01``, ``00``;
    codes without a statistical suffix return STAT_SUFFIX None and HTS_CODE = full code.
    """
    stripped = htsno.strip()
    if not stripped:
        return None, None

    parts = stripped.split(".")
    last = parts[-1]

    if len(parts) >= 4 and len(last) == 2 and last.isdigit():
        return ".".join(parts[:-1]), last

    if len(parts) == 3 and len(last) == 4 and last.isdigit():
        stat = last[2:]
        head = last[:2]
        return f"{parts[0]}.{parts[1]}.{head}", stat

    if "." not in stripped:
        digits = _NON_DIGIT.sub("", stripped)
        if len(digits) == 10 and digits.isdigit():
            base = f"{digits[:4]}.{digits[4:6]}.{digits[6:8]}"
            return base, digits[8:10]

    return stripped, None


def _indent_level(raw: Dict[str, Any]) -> Optional[int]:
    val = raw.get("indent")
    if val is None or val == "":
        return None
    try:
        return int(str(val).strip())
    except ValueError:
        return None


def _footnotes_json(raw: Dict[str, Any]) -> str:
    fn = raw.get("footnotes")
    if fn is None:
        return json.dumps([], ensure_ascii=False)
    if isinstance(fn, list):
        return json.dumps(fn, ensure_ascii=False)
    if isinstance(fn, str):
        s = fn.strip()
        if s.startswith("["):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return json.dumps(parsed, ensure_ascii=False)
            except json.JSONDecodeError:
                pass
        return json.dumps([fn], ensure_ascii=False)
    return json.dumps([fn], ensure_ascii=False)


def parse_records(raw: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    """
    Transform API rows into dicts aligned with the HTS_CODES table (no HTS_ID).

    Header rows (missing/blank ``htsno``) are kept with ``IS_HEADER_ROW`` True.

    Returns (cleaned_records, header_row_count).
    """
    logger.info("Starting parse of %s raw records", len(raw))
    cleaned: List[Dict[str, Any]] = []
    header_rows = 0

    for rec in raw:
        hts = rec.get("htsno")
        is_header = hts is None or (isinstance(hts, str) and not str(hts).strip())
        if is_header:
            header_rows += 1
            code_str: Optional[str] = None
            hts_code: Optional[str] = None
            stat_suffix: Optional[str] = None
        else:
            code_str = str(hts).strip()
            hts_code, stat_suffix = _split_hts_and_stat_suffix(code_str)

        description = rec.get("description")
        desc_str = str(description).strip() if description is not None else ""

        def _rate(key: str) -> str:
            v = rec.get(key)
            if v is None:
                return ""
            return str(v).strip()

        units_val = rec.get("units")
        units_str = str(units_val).strip() if units_val is not None else ""

        chapter = _chapter_number(code_str) if code_str else None

        cleaned.append(
            {
                "HTS_CODE": hts_code,
                "STAT_SUFFIX": stat_suffix,
                "CHAPTER": chapter,
                "SECTION_NUMBER": _section_number(chapter),
                "LEVEL": _hts_level(code_str),
                "DESCRIPTION": desc_str[:2000],
                "GENERAL_RATE": _rate("general")[:200],
                "SPECIAL_RATE": _rate("special")[:500],
                "OTHER_RATE": _rate("other")[:200],
                "UNITS": units_str[:100],
                "INDENT_LEVEL": _indent_level(rec),
                "IS_HEADER_ROW": is_header,
                "FOOTNOTES": _footnotes_json(rec),
                "RAW_JSON": json.dumps(rec, ensure_ascii=False),
            }
        )

    logger.info(
        "Parse completed; %s records (%s header rows with empty htsno)",
        len(cleaned),
        header_rows,
    )
    return cleaned, header_rows
