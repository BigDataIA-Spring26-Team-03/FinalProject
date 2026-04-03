# TariffIQ HTS POC

This repository is a small proof-of-concept that downloads the current U.S. Harmonized Tariff Schedule from the USITC’s public REST API, normalizes each row to match a Snowflake staging table, and loads them into `TARIFFIQ.RAW.HTS_CODES`. The pipeline is a single Python script with no orchestration framework: one HTTP export, in-memory parsing, and batched idempotent inserts via `snowflake-connector-python`.

The USITC **HTS System User Guide** documents the REST API. For a full JSON export, `GET /exportList` must include the required query parameters `format`, `from`, and `to` (and optionally `styles`). This project uses a single request spanning `from=0101` through `to=9999`, which returns the full export (on the order of 35,700 rows). Many of those rows are valid tariff lines with an `htsno`; others are structural lines with an empty `htsno` and are skipped during parsing, as required. Narrower `from`/`to` ranges use the same endpoint if you prefer to chunk by chapter.

## Setup

1. Clone the repository and change into the project directory.
2. Create a virtual environment and install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Copy the environment template and add your Snowflake credentials:

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD`, `SNOWFLAKE_ACCOUNT`, and `SNOWFLAKE_WAREHOUSE`. Optionally override `SNOWFLAKE_DATABASE` (default `TARIFFIQ`) and `SNOWFLAKE_SCHEMA` (default `RAW`).

4. Run the pipeline from the project root:

   ```bash
   python main.py
   ```

## Sample output

On a successful run, logging shows each major step (API request, parse, Snowflake batches), and the script ends with a short summary similar to:

```
2026-04-02 14:32:01 — INFO — Pipeline started
2026-04-02 14:32:01 — INFO — Starting HTS export API request (from=0101, to=9999)
2026-04-02 14:32:04 — INFO — HTS export API completed; received 35733 records
2026-04-02 14:32:04 — INFO — Starting parse of 35733 raw records
2026-04-02 14:32:04 — INFO — Parse completed; 29807 records kept, 5926 skipped (missing HTS code)
2026-04-02 14:32:04 — INFO — Starting Snowflake load for 29807 records
Snowflake batches: 100%|██████████| 6/6 [00:38<00:00,  6.34s/batch]
2026-04-02 14:32:50 — INFO — Loaded batch ending at index 5000 (5000 rows in batch, rowcount=5000)
...
2026-04-02 14:32:50 — INFO — Snowflake load completed; rows inserted this run: 29807
2026-04-02 14:32:50 — INFO — Pipeline finished successfully

Summary
-------
  Total fetched: 35733
  Total parsed:  29807
  Total loaded:  29807
  Skipped (null/empty HTS code): 5926
```

Re-running against the same data loads zero new rows when every `HTS_CODE` already exists, because inserts use a `WHERE NOT EXISTS` guard.
