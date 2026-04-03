"""Orchestrate fetch → parse → load for USITC HTS data into Snowflake."""

import logging
import sys

import requests

from src.fetch import fetch_hts_records
from src.load import load_to_snowflake
from src.parse import parse_records

LOG_FORMAT = "%(asctime)s — %(levelname)s — %(message)s"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    logger = logging.getLogger(__name__)

    try:
        logger.info("Pipeline started")
        raw = fetch_hts_records()
        parsed, header_rows = parse_records(raw)
        loaded = load_to_snowflake(parsed)
        logger.info("Pipeline finished successfully")

        print()
        print("Summary")
        print("-------")
        print(f"  Total fetched: {len(raw)}")
        print(f"  Total parsed:  {len(parsed)}")
        print(f"  Total loaded:  {loaded}")
        print(f"  Header rows (empty htsno): {header_rows}")
        print()
    except requests.HTTPError as exc:
        logger.error("HTTP error from HTS API: %s", exc)
        sys.exit(1)
    except requests.RequestException as exc:
        logger.error("Request to HTS API failed: %s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.exception("Pipeline failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
