"""Live Census Bureau international trade (imports) API — no bulk cache."""

import logging
import time
from datetime import date
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)

CENSUS_BASE = "https://api.census.gov/data/timeseries/intltrade/imports/hs"

COUNTRY_CODES = {
    "5700": "China",
    "2010": "Mexico",
    "1220": "Canada",
    "5490": "Japan",
    "5820": "South Korea",
    "4120": "Germany",
    "5350": "Vietnam",
    "5030": "India",
    "4790": "United Kingdom",
    "5080": "Taiwan",
}


def _month_subtract(year: int, month: int, delta: int) -> tuple:
    """Return (year, month) for `delta` months before (year, month)."""
    m = month - delta
    y = year
    while m <= 0:
        m += 12
        y -= 1
    while m > 12:
        m -= 12
        y += 1
    return y, m


def _build_request_url(params: Dict[str, str]) -> str:
    return f"{CENSUS_BASE}?{urlencode(params)}"


def get_trade_value(
    hs_code: str,
    country_code: str,
    year: int,
    month: int,
    comm_lvl: str = "HS4",
    timeout: int = 15,
) -> Optional[Dict[str, Any]]:
    """
    Single live Census query. Returns a dict of column -> value, or None if no data.
    """
    params = {
        "get": "GEN_VAL_MO,GEN_QY1_MO,CTY_NAME,I_COMMODITY_SDESC",
        "COMM_LVL": comm_lvl,
        "I_COMMODITY": hs_code,
        "CTY_CODE": country_code,
        "YEAR": str(year),
        "MONTH": str(month).zfill(2),
    }
    url = _build_request_url(params)
    response = requests.get(url, timeout=timeout)

    if response.status_code == 204:
        return None
    if response.status_code != 200:
        raise RuntimeError(f"Census API HTTP {response.status_code} for {url}")

    data = response.json()
    if not isinstance(data, list) or len(data) < 2:
        return None

    headers = data[0]
    row = data[1]
    out = dict(zip(headers, row))

    val = out.get("GEN_VAL_MO")
    logger.info(
        "Census trade hs=%s country=%s %04d-%02d import_value_usd=%s",
        hs_code,
        country_code,
        year,
        month,
        val,
    )
    return out


def _parse_int_field(raw: Any) -> Optional[int]:
    if raw is None or raw == "":
        return None
    try:
        return int(str(raw).replace(",", ""))
    except ValueError:
        return None


def get_trend(
    hs_code: str,
    country_code: str,
    months_back: int = 12,
    comm_lvl: str = "HS4",
) -> List[Dict[str, Any]]:
    """
    Call get_trade_value for each of the past `months_back` calendar months (from today),
    with 150ms delay between requests. Returns sorted ascending by period.
    """
    today = date.today()
    y0, m0 = today.year, today.month
    collected: List[Dict[str, Any]] = []

    for i in range(months_back):
        y, m = _month_subtract(y0, m0, i)
        row = get_trade_value(hs_code, country_code, y, m, comm_lvl=comm_lvl)
        if row is None:
            if i < months_back - 1:
                time.sleep(0.15)
            continue

        period = f"{y}-{str(m).zfill(2)}"
        collected.append(
            {
                "period": period,
                "import_value_usd": _parse_int_field(row.get("GEN_VAL_MO")),
                "import_quantity": _parse_int_field(row.get("GEN_QY1_MO")),
                "country_name": str(row.get("CTY_NAME") or COUNTRY_CODES.get(country_code, "")),
                "commodity_desc": str(row.get("I_COMMODITY_SDESC") or ""),
            }
        )
        if i < months_back - 1:
            time.sleep(0.15)

    collected.sort(key=lambda r: r["period"])
    return collected
