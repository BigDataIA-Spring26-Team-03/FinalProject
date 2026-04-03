"""Fetch HTS records from the USITC REST API."""

import logging
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)

API_BASE = "https://hts.usitc.gov/reststop"
# Per USITC HTS External User Guide: exportList requires format, from, and to.
# A single range covering the full schedule returns all tariff lines (e.g. ~35,733 rows).
DEFAULT_EXPORT_FROM = "0101"
DEFAULT_EXPORT_TO = "9999"


def fetch_hts_records(
    export_from: str = DEFAULT_EXPORT_FROM,
    export_to: str = DEFAULT_EXPORT_TO,
    *,
    include_styles: bool = False,
    timeout: int = 60,
) -> List[Dict[str, Any]]:
    """
    Call GET /exportList with required query parameters and return the raw list of dicts.

    See: HTS System User Guide — RESTful API — Export (exportList).
    """
    url = f"{API_BASE}/exportList"
    params = {
        "from": export_from,
        "to": export_to,
        "format": "JSON",
        "styles": "true" if include_styles else "false",
    }
    logger.info("Starting HTS export API request (from=%s, to=%s)", export_from, export_to)
    response = requests.get(url, params=params, timeout=timeout)
    if response.status_code != 200:
        logger.error("HTS export API returned HTTP %s", response.status_code)
        response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        logger.error("Unexpected API payload type: %s", type(data).__name__)
        raise ValueError("exportList response must be a JSON array")
    logger.info("HTS export API completed; received %s records", len(data))
    return data
