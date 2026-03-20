# Ingest Flows

This explains how EIA energy data gets from the internet into your database — what each dataset contains, how to run and debug ingest jobs, and how to build out a historical dataset.

---

## What is "ingest"?

Ingest is the process of fetching data from the EIA API and saving it to the database. Think of it like a scheduled download that runs automatically, checks for new data each month, and writes it to Postgres in a format ready for querying and visualization.

There are four datasets ("flows"), each corresponding to a database table:

| Flow | Table | What it contains |
|------|-------|-----------------|
| `retail_sales` | `eia_retail_sales` | Monthly electricity sales, revenue, price per kWh, and customer counts — broken down by state and sector (residential, commercial, industrial, transport) |
| `electric_power_operational` | `eia_electric_power_operational` | Monthly electricity generation by state, sector, and fuel type (coal, gas, nuclear, wind, solar, etc.) |
| `state_source_disposition` | `eia_state_source_disposition` | Monthly net interstate electricity trade and total disposition — how much electricity states import/export from each other |
| `state_summary` | `eia_state_summary` | Annual summary per state: average retail price, total generation, total consumption |

---

## Two ways to run ingest

### Option 1: Local (recommended for building historical data)

Runs the flow directly in your terminal — no Prefect server needed. You get full Python error messages if something goes wrong.

```bash
# Single dataset, specific date range
make backfill DATASET=retail_sales START=2020-01 END=2024-12

# All four datasets
make backfill DATASET=all START=2015-01 END=2024-12

# Break a long range into 6-month chunks (uses less memory per run)
make backfill DATASET=all START=2010-01 END=2024-12 CHUNKS=6
```

**When to use this:** Always start here when testing new ingest code or building out historical data. It's faster to debug because errors appear immediately in the terminal.

### Option 2: Via Prefect (production path)

Runs through the Prefect job scheduler. Lets you monitor progress in the Prefect UI, retry failed jobs, and set up recurring schedules.

```bash
# Requires the Docker stack to be running (make up)
make backfill-prefect DATASET=retail_sales START=2020-01 END=2024-12
```

Then watch progress at http://localhost:4200.

**When to use this:** After you've confirmed the ingest works locally and you want to run it on a schedule or trigger it from the Prefect UI.

---

## How ingest works (under the hood)

Each flow does two things:

1. **Fetch**: Calls the EIA API, paginating through results 5,000 rows at a time until all data for the date range is downloaded
2. **Upsert**: Writes each row to Postgres using `INSERT ... ON CONFLICT DO UPDATE` — so running the same job twice is safe, it just updates existing rows rather than creating duplicates

The date range parameters (`START`, `END`) are in `YYYY-MM` format. If you omit them, the flow defaults to last calendar month.

For large backfills, use `CHUNKS` to split the work. For example, `CHUNKS=6` runs one 6-month batch at a time:
```
2010-01 → 2010-06  (first batch)
2010-07 → 2010-12  (second batch)
...
2024-07 → 2024-12  (last batch)
```

---

## Debugging a failed ingest

If you see an error, run the failing flow locally to get a full traceback:

```bash
make backfill DATASET=retail_sales START=2023-01 END=2023-01
```

Common errors:

**`EIA_API_KEY` not set or invalid**
Check your `.env` file. The EIA API returns a 403 error if the key is missing or wrong.

**`DATABASE_URL` not set**
Make sure `.env` has `INGEST_DATABASE_URL` pointing to a running Postgres.

**Connection timeout / EIA API slow**
The EIA API occasionally times out under load. The code automatically retries up to 5 times with exponential backoff. If it keeps failing, try again later or reduce `EIA_MAX_CONCURRENT_REQUESTS` in `.env`.

**`relation "eia_retail_sales" does not exist`**
The ingest database tables haven't been created. Run:
```bash
# Docker stack
./dock.sh ensure-ingest-db

# Local Postgres
for f in docker/postgres/init/ingest/*.sql; do psql -d ingest -f "$f"; done
```

---

## Checking what's in the database

After a backfill, check row counts and date ranges using DBeaver or the pgweb browser (http://localhost:8080):

```sql
-- Row counts per table
SELECT 'eia_retail_sales' AS table_name, COUNT(*), MIN(period), MAX(period) FROM eia_retail_sales
UNION ALL
SELECT 'eia_electric_power_operational', COUNT(*), MIN(period), MAX(period) FROM eia_electric_power_operational
UNION ALL
SELECT 'eia_state_source_disposition', COUNT(*), MIN(period), MAX(period) FROM eia_state_source_disposition
UNION ALL
SELECT 'eia_state_summary', COUNT(*), MIN(period), MAX(period) FROM eia_state_summary;
```

---

## Scheduled ingest (production)

When deployed on Proxmox, Prefect runs ingest automatically on the 1st of each month, picking up the previous month's data. No manual action needed after the initial backfill.

To register the monthly schedules:
```bash
make deploy   # (requires the Docker stack or Proxmox app LXC to be running)
```
