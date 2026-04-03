"""Source 3 live demo: Snowflake (Sources 1+2) + Census Bureau trade API (no bulk load)."""

import logging
import sys
import time
from typing import Any, Dict, List, Optional

import snowflake.connector
from tabulate import tabulate

from config import settings
from src.source3.fetch import _build_request_url, get_trade_value, get_trend
from src.source3.query import get_hts_info, get_policy_docs

LOG_FORMAT = "%(asctime)s — %(levelname)s — %(message)s"

DEMO_HTS_PREFIX = "8471"
DEMO_COUNTRY = "5700"
DEMO_YEAR = 2025
DEMO_MONTH = 10
DEMO_COMM_LVL = "HS4"


def _tabulate_dicts(rows: List[Dict[str, Any]], headers: Optional[List[str]] = None) -> str:
    if not rows:
        return "(no rows)"
    cols = headers if headers is not None else list(rows[0].keys())
    table = [[r.get(c) for c in cols] for r in rows]
    return tabulate(table, headers=[c.upper() for c in cols], tablefmt="pretty")


def _trend_stats(trend: List[Dict[str, Any]]) -> tuple:
    """(high_period, high_val, low_period, low_val, first_val, last_val, pct_change_str)"""
    with_vals = [(r["period"], r["import_value_usd"]) for r in trend if r.get("import_value_usd") is not None]
    if not with_vals:
        return ("N/A", None, "N/A", None, None, None, "N/A")
    high = max(with_vals, key=lambda x: x[1])
    low = min(with_vals, key=lambda x: x[1])
    first_val = trend[0].get("import_value_usd") if trend else None
    last_val = trend[-1].get("import_value_usd") if trend else None
    if first_val is not None and last_val is not None and first_val != 0:
        pct = (last_val - first_val) / first_val * 100.0
        pct_str = f"{pct:+.1f}"
    else:
        pct_str = "N/A"
    return (high[0], high[1], low[0], low[1], first_val, last_val, pct_str)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    logger = logging.getLogger(__name__)

    wall_start = time.perf_counter()
    snowflake_seconds = 0.0
    census_seconds = 0.0

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
        sys.exit(1)

    try:
        # Step 1 — Source 1
        t0 = time.perf_counter()
        hts_rows = get_hts_info(conn, DEMO_HTS_PREFIX)
        t1 = time.perf_counter()
        snowflake_seconds += t1 - t0

        print()
        print("SOURCE 1 — HTS Product Classifications (Snowflake)")
        print()
        if not hts_rows:
            logger.warning("No HTS rows returned for prefix %s", DEMO_HTS_PREFIX)
            print("(no rows)")
        else:
            print(_tabulate_dicts(hts_rows))
        print()

        # Step 2 — Source 2
        t0 = time.perf_counter()
        policy_rows = get_policy_docs(conn, DEMO_HTS_PREFIX)
        t1 = time.perf_counter()
        snowflake_seconds += t1 - t0

        print("SOURCE 2 — Federal Register Policy Documents (Snowflake)")
        print()
        if not policy_rows:
            logger.warning("No Federal Register rows returned for prefix %s", DEMO_HTS_PREFIX)
            print("(no rows)")
        else:
            print(_tabulate_dicts(policy_rows))
        print()

        # Step 3 — Census single month
        census_params = {
            "get": "GEN_VAL_MO,GEN_QY1_MO,CTY_NAME,I_COMMODITY_SDESC",
            "COMM_LVL": DEMO_COMM_LVL,
            "I_COMMODITY": DEMO_HTS_PREFIX,
            "CTY_CODE": DEMO_COUNTRY,
            "YEAR": str(DEMO_YEAR),
            "MONTH": str(DEMO_MONTH).zfill(2),
        }
        census_url = _build_request_url(census_params)

        print("SOURCE 3 — Live Census API Call (real-time)")
        print()
        print(f"URL: {census_url}")
        print()

        t0 = time.perf_counter()
        trade_row = get_trade_value(
            DEMO_HTS_PREFIX,
            DEMO_COUNTRY,
            DEMO_YEAR,
            DEMO_MONTH,
            comm_lvl=DEMO_COMM_LVL,
        )
        t1 = time.perf_counter()
        census_seconds += t1 - t0

        if trade_row is None:
            print("No data available for this period")
            trade_val_display: Optional[int] = None
        else:
            print(trade_row)
            trade_val_display = None
            try:
                trade_val_display = int(str(trade_row.get("GEN_VAL_MO", "")).replace(",", ""))
            except ValueError:
                trade_val_display = None
        print()

        # Step 4 — 12-month trend
        t0 = time.perf_counter()
        trend = get_trend(DEMO_HTS_PREFIX, DEMO_COUNTRY, months_back=12, comm_lvl=DEMO_COMM_LVL)
        t1 = time.perf_counter()
        census_seconds += t1 - t0

        print("SOURCE 3 — 12-Month Import Trend (China, HS4 8471)")
        print()
        trend_table = [
            {
                "PERIOD": r["period"],
                "IMPORT_VALUE_USD": r["import_value_usd"],
                "IMPORT_QUANTITY": r["import_quantity"],
                "COUNTRY": r["country_name"],
            }
            for r in trend
        ]
        if trend_table:
            print(_tabulate_dicts(trend_table, headers=["PERIOD", "IMPORT_VALUE_USD", "IMPORT_QUANTITY", "COUNTRY"]))
        else:
            print("(no trend rows)")
        hi_p, hi_v, lo_p, lo_v, first_v, last_v, pct_str = _trend_stats(trend)
        print()
        if hi_v is not None:
            print(f"Highest import value month : {hi_p} (${hi_v:,})")
        else:
            print("Highest import value month : N/A")
        if lo_v is not None:
            print(f"Lowest import value month  : {lo_p} (${lo_v:,})")
        else:
            print("Lowest import value month  : N/A")
        if first_v is not None and last_v is not None:
            print(f"Change first → last month  : ${first_v:,} → ${last_v:,} ({pct_str}%)")
        else:
            print("Change first → last month  : N/A")
        print()

        # Step 5 — Combined answer
        h1 = hts_rows[0] if hts_rows else {}
        p1 = policy_rows[0] if policy_rows else {}

        prod = h1.get("DESCRIPTION") or "N/A"
        hts_code = h1.get("HTS_CODE") or "N/A"
        gen = h1.get("GENERAL_RATE") or "N/A"
        spec = h1.get("SPECIAL_RATE") or "N/A"
        pol_title = p1.get("TITLE") or "N/A"
        pol_date = p1.get("PUBLICATION_DATE") or "N/A"
        if hasattr(pol_date, "isoformat"):
            pol_date = pol_date.isoformat()
        pol_ref = p1.get("HTML_URL") or "N/A"
        pol_ctx = (p1.get("CONTEXT_SNIPPET") or "N/A") if p1 else "N/A"
        if len(str(pol_ctx)) > 200:
            pol_ctx = str(pol_ctx)[:197] + "..."

        if trade_val_display is not None:
            vol_line = f"${trade_val_display:,} (Oct 2025, from China)"
        else:
            vol_line = "No data available for this period"

        if first_v is not None and last_v is not None:
            trend_line = f"${first_v:,} → ${last_v:,} ({pct_str}%)"
        else:
            trend_line = "N/A"

        print("============================================================")
        print("TARIFFIQ AI — THREE-SOURCE COMBINED ANSWER")
        print("============================================================")
        print(f"Product        : {prod}")
        print(f"HTS Code       : {hts_code}")
        print("------------------------------------------------------------")
        print(f"BASE RATE      : {gen}")
        print(f"SPECIAL RATE   : {spec}")
        print("------------------------------------------------------------")
        print(f"POLICY ACTION  : {pol_title}")
        print(f"POLICY DATE    : {pol_date}")
        print(f"POLICY REF     : {pol_ref}")
        print(f"CONTEXT        : {pol_ctx}")
        print("------------------------------------------------------------")
        print(f"TRADE VOLUME   : {vol_line}")
        print(f"TREND          : {trend_line}")
        print("------------------------------------------------------------")
        print("DATA SOURCES   : USITC HTS API + Federal Register API + Census Bureau API")
        print("============================================================")
        print()

        wall_end = time.perf_counter()
        print(f"Snowflake query time : {snowflake_seconds:.2f}s")
        print(f"Census API call time : {census_seconds:.2f}s")
        print(f"Total wall time      : {wall_end - wall_start:.2f}s")
        print()

    except Exception as exc:
        logger.exception("Source 3 pipeline failed: %s", exc)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
