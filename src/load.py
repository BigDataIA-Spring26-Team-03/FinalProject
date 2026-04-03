"""Load parsed HTS rows into Snowflake."""

import logging
import sys
from typing import Any, Dict, List, Sequence

import snowflake.connector
from tqdm import tqdm

from config import settings

logger = logging.getLogger(__name__)

BATCH_SIZE = 5000

DDL_TABLE = """
CREATE TABLE IF NOT EXISTS HTS_CODES (
    HTS_ID          NUMBER(38,0)    IDENTITY(1,1),
    HTS_CODE        VARCHAR(20),
    STAT_SUFFIX     VARCHAR(2),
    CHAPTER         NUMBER(2),
    SECTION_NUMBER  NUMBER(2),
    LEVEL           VARCHAR(20),
    DESCRIPTION     VARCHAR(2000),
    GENERAL_RATE    VARCHAR(200),
    SPECIAL_RATE    VARCHAR(500),
    OTHER_RATE      VARCHAR(200),
    UNITS           VARCHAR(100),
    INDENT_LEVEL    NUMBER(2),
    IS_HEADER_ROW   BOOLEAN,
    FOOTNOTES       ARRAY,
    RAW_JSON        VARIANT,
    LOADED_AT       TIMESTAMP_NTZ   DEFAULT CURRENT_TIMESTAMP()
)
"""

INSERT_SQL = """
INSERT INTO HTS_CODES (
    HTS_CODE,
    STAT_SUFFIX,
    CHAPTER,
    SECTION_NUMBER,
    LEVEL,
    DESCRIPTION,
    GENERAL_RATE,
    SPECIAL_RATE,
    OTHER_RATE,
    UNITS,
    INDENT_LEVEL,
    IS_HEADER_ROW,
    FOOTNOTES,
    RAW_JSON
)
SELECT
    v.c1,
    v.c2,
    v.c3,
    v.c4,
    v.c5,
    v.c6,
    v.c7,
    v.c8,
    v.c9,
    v.c10,
    v.c11,
    v.c12,
    CAST(PARSE_JSON(v.c13) AS ARRAY),
    PARSE_JSON(v.c14)
FROM (VALUES {values_clause}) AS v(
    c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12, c13, c14
)
"""


def _values_clause(n_rows: int) -> str:
    return ", ".join(n_rows * ["(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"])


def _flatten_batch(batch: Sequence[Dict[str, Any]]) -> List[Any]:
    flat: List[Any] = []
    for row in batch:
        flat.extend(
            [
                row["HTS_CODE"],
                row["STAT_SUFFIX"],
                row["CHAPTER"],
                row["SECTION_NUMBER"],
                row["LEVEL"],
                row["DESCRIPTION"],
                row["GENERAL_RATE"],
                row["SPECIAL_RATE"],
                row["OTHER_RATE"],
                row["UNITS"],
                row["INDENT_LEVEL"],
                row["IS_HEADER_ROW"],
                row["FOOTNOTES"],
                row["RAW_JSON"],
            ]
        )
    return flat


def load_to_snowflake(records: List[Dict[str, Any]]) -> int:
    """
    Ensure database/schema/table exist, truncate HTS_CODES, then load in batches.

    Each run replaces table contents (idempotent full refresh).
    """
    logger.info("Starting Snowflake load for %s records", len(records))
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
        raise

    total_inserted = 0
    try:
        with conn.cursor() as cur:
            cur.execute(f'CREATE DATABASE IF NOT EXISTS "{settings.SNOWFLAKE_DATABASE}"')
            cur.execute(f'USE DATABASE "{settings.SNOWFLAKE_DATABASE}"')
            cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{settings.SNOWFLAKE_SCHEMA}"')
            cur.execute(f'USE SCHEMA "{settings.SNOWFLAKE_SCHEMA}"')
            cur.execute(DDL_TABLE)
            cur.execute("TRUNCATE TABLE IF EXISTS HTS_CODES")
            logger.info("Truncated HTS_CODES prior to load")

            for i in tqdm(
                range(0, len(records), BATCH_SIZE),
                desc="Snowflake batches",
                unit="batch",
            ):
                batch = records[i : i + BATCH_SIZE]
                n = len(batch)
                sql = INSERT_SQL.format(values_clause=_values_clause(n))
                params = _flatten_batch(batch)
                cur.execute(sql, params)
                total_inserted += cur.rowcount or 0
                logger.info(
                    "Loaded batch ending at index %s (%s rows in batch, rowcount=%s)",
                    i + n,
                    n,
                    cur.rowcount,
                )
        conn.commit()
    finally:
        conn.close()

    logger.info("Snowflake load completed; rows inserted this run: %s", total_inserted)
    return total_inserted
