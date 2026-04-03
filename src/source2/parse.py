"""Parse Federal Register metadata and clean HTML to plain text."""

import json
import re
from typing import Any, Dict, Optional

from bs4 import BeautifulSoup

_WS = re.compile(r"\s+")


def parse_document(raw_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Map API metadata to flat uppercase keys for Snowflake staging."""
    agencies = raw_doc.get("agencies") or []
    names = []
    if isinstance(agencies, list):
        for a in agencies:
            if isinstance(a, dict) and a.get("name"):
                names.append(str(a["name"]).strip())
    agency_names = ", ".join(names)

    title = raw_doc.get("title")
    title_str = str(title).strip() if title is not None else ""

    pub = raw_doc.get("publication_date")
    pub_str: Optional[str]
    if pub is None or pub == "":
        pub_str = None
    else:
        s = str(pub).strip()
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            pub_str = s[:10]
        else:
            pub_str = s[:10] if len(s) >= 10 else s

    # API exposes document kind as `type` (not `document_type`); keep fallback for tests/mocks.
    doc_type = raw_doc.get("type")
    if doc_type is None:
        doc_type = raw_doc.get("document_type")
    doc_type_str = str(doc_type) if doc_type is not None else ""

    abstract = raw_doc.get("abstract")
    if abstract is None:
        abstract_str = None
    else:
        stripped = str(abstract).strip()
        abstract_str = stripped if stripped else None

    html_url = raw_doc.get("html_url")
    body_html_url = raw_doc.get("body_html_url")

    return {
        "DOCUMENT_NUMBER": raw_doc.get("document_number"),
        "TITLE": title_str[:1000],
        "PUBLICATION_DATE": pub_str,
        "DOCUMENT_TYPE": doc_type_str[:50] if doc_type_str else "",
        "AGENCY_NAMES": agency_names[:500],
        "ABSTRACT": abstract_str[:2000] if abstract_str else None,
        "HTML_URL": str(html_url)[:500] if html_url else None,
        "BODY_HTML_URL": str(body_html_url)[:500] if body_html_url else None,
        "RAW_JSON": json.dumps(raw_doc, ensure_ascii=False),
    }


def clean_html(raw_html: Optional[str]) -> Optional[str]:
    """Strip HTML tags and collapse whitespace. Returns None if input is None."""
    if raw_html is None:
        return None
    try:
        soup = BeautifulSoup(raw_html, "html.parser")
        text = soup.get_text(separator=" ")
    except Exception:
        raise
    text = _WS.sub(" ", text).strip()
    return text if text else None
