"""Cached Snowflake connection shared across all Streamlit pages."""

import sys
from pathlib import Path

# Ensure FinalProject root is on the path so config/ is importable
ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import snowflake.connector
from config import settings


@st.cache_resource
def get_connection():
    """Create (and cache) a single Snowflake connection for the lifetime of the app."""
    conn = snowflake.connector.connect(
        user=settings.SNOWFLAKE_USER,
        password=settings.SNOWFLAKE_PASSWORD,
        account=settings.SNOWFLAKE_ACCOUNT,
        warehouse=settings.SNOWFLAKE_WAREHOUSE,
        database=settings.SNOWFLAKE_DATABASE,
        schema=settings.SNOWFLAKE_SCHEMA,
    )
    return conn


def run_query(sql: str, params=None) -> list:
    """Execute a SQL query and return rows as a list of dicts."""
    conn = get_connection()
    with conn.cursor() as cur:
        if params:
            cur.execute(sql, params)
        else:
            cur.execute(sql)
        columns = [c[0] for c in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]
