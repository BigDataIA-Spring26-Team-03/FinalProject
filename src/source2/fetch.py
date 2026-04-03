"""Fetch Federal Register document metadata and full-text HTML."""

import logging
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

API_URL = "https://www.federalregister.gov/api/v1/documents.json"

# Slug from GET /api/v1/agencies.json ("Trade Representative, Office of United States").
# The informal slug office-of-the-united-states-trade-representative is rejected (400 invalid agencies).
USTR_AGENCY_SLUG = "trade-representative-office-of-united-states"


def _list_params() -> List[tuple]:
    return [
        ("conditions[agencies][]", USTR_AGENCY_SLUG),
        ("conditions[term]", "tariff"),
        ("conditions[publication_date][gte]", "2018-01-01"),
        ("per_page", "20"),
        ("order", "newest"),
        ("fields[]", "document_number"),
        ("fields[]", "title"),
        ("fields[]", "publication_date"),
        ("fields[]", "type"),
        ("fields[]", "abstract"),
        ("fields[]", "html_url"),
        ("fields[]", "body_html_url"),
        ("fields[]", "agencies"),
    ]


def fetch_documents(timeout: int = 60) -> List[Dict[str, Any]]:
    """
    Page through all Federal Register documents matching the fixed filter.
    Returns a flat list of metadata dicts.
    """
    all_docs: List[Dict[str, Any]] = []
    url: Optional[str] = API_URL
    page_params: Optional[List[tuple]] = _list_params()
    page_idx = 0

    logger.info("Starting Federal Register document fetch")
    while url:
        page_idx += 1
        if page_params is not None:
            response = requests.get(url, params=page_params, timeout=timeout)
            page_params = None
        else:
            response = requests.get(url, timeout=timeout)

        if response.status_code != 200:
            detail = ""
            try:
                detail = response.text[:500]
            except Exception:
                pass
            logger.error(
                "Federal Register API returned HTTP %s for %s — %s",
                response.status_code,
                url,
                detail,
            )
            response.raise_for_status()

        payload = response.json()
        batch = payload.get("results") or []
        all_docs.extend(batch)
        logger.info(
            "Fetched page %s (%s documents, running total %s)",
            page_idx,
            len(batch),
            len(all_docs),
        )

        next_url = payload.get("next_page_url")
        url = next_url if next_url else None

    logger.info("Federal Register fetch completed; total documents: %s", len(all_docs))
    return all_docs


def fetch_full_text(body_html_url: Optional[str], timeout: int = 30) -> Optional[str]:
    """Download raw HTML for a document body. Returns None if URL is missing."""
    if body_html_url is None:
        return None
    url = str(body_html_url).strip()
    if not url:
        return None
    response = requests.get(url, timeout=timeout)
    if response.status_code != 200:
        logger.error(
            "Body HTML fetch returned HTTP %s for %s",
            response.status_code,
            url,
        )
        response.raise_for_status()
    return response.text
