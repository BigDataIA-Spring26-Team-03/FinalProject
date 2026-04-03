"""Application settings loaded from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise ValueError(f"Missing required environment variable: {name}")
    return value


SNOWFLAKE_USER = _require("SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD = _require("SNOWFLAKE_PASSWORD")
SNOWFLAKE_ACCOUNT = _require("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_WAREHOUSE = _require("SNOWFLAKE_WAREHOUSE")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE", "TARIFFIQ").strip()
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA", "RAW").strip()
