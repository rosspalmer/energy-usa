# Schema Migration & Code Restructuring — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename `ingest.eia_*` tables to `eia.*` (source-as-schema), restructure Python packages into nested directories by source, add transform database, and update all references — without breaking existing functionality.

**Architecture:** The flat `db/`, `flows/`, and `eia/` packages become nested: `db/ingest/eia/`, `flows/ingest/eia/`, `clients/eia.py`. Docker init SQL moves from numbered files in `docker/postgres/init/ingest/` to `docker/postgres/init/ingest/eia/<table>.sql`. A new `transform` database is created but left empty (populated by Plan 4). The `quality` schema is created in the ingest database.

**Tech Stack:** Python 3.12, psycopg3, Prefect 2, PostgreSQL 16, Docker Compose, uv

**Design Spec:** `docs/superpowers/specs/2026-04-10-markdown-driven-data-platform-design.md`

---

## File Map

### Created
```
docker/postgres/init/01-create-databases.sql
docker/postgres/init/03-run-init-scripts.sh       (replaces existing)
docker/postgres/init/ingest/eia/00-schema.sql
docker/postgres/init/ingest/eia/<table>.sql        (36 files, renamed from NN-<table>.sql)
docker/postgres/init/ingest/00-quality-schema.sql
docker/postgres/init/transform/00-create-schema-placeholder.sql
deploy/migrations/001-rename-eia-schemas.sql
src/energy_usa/clients/__init__.py
src/energy_usa/clients/base.py
src/energy_usa/clients/eia.py                      (consolidated from eia/client.py + eia/manager.py)
src/energy_usa/db/connection.py                    (extracted from db/retail_sales.py)
src/energy_usa/db/ingest/__init__.py
src/energy_usa/db/ingest/eia/__init__.py
src/energy_usa/db/ingest/eia/<table>.py            (36 files, moved from db/<table>.py)
src/energy_usa/flows/ingest/__init__.py
src/energy_usa/flows/ingest/eia/__init__.py
src/energy_usa/flows/ingest/eia/<table>.py         (36 files, moved from flows/eia_<table>.py)
src/energy_usa/flows/ingest/backfill.py            (replaces flows/backfill_eia.py)
tests/unit/db/__init__.py
tests/unit/db/ingest/__init__.py
tests/unit/db/ingest/eia/__init__.py
tests/unit/db/ingest/eia/test_upsert_normalization.py
tests/integration/db/__init__.py
tests/integration/db/ingest/__init__.py
tests/integration/db/ingest/eia/__init__.py
tests/integration/db/ingest/eia/test_db_upserts.py
```

### Deleted (after moves)
```
docker/postgres/init/02-create-ingest-db.sql
docker/postgres/init/03-create-superset-db.sql
docker/postgres/init/ingest/00-schema.sql
docker/postgres/init/ingest/01-retail-sales.sql ... 36-ieo.sql   (36 files)
src/energy_usa/eia/                                (entire directory)
src/energy_usa/db/retail_sales.py ... ieo.py       (36 files, not period.py/dataframe.py)
src/energy_usa/flows/eia_retail_sales.py ... eia_total_energy.py  (36 files)
src/energy_usa/flows/backfill_eia.py
tests/unit/test_upsert_normalization.py
tests/integration/test_db_upserts.py
```

### Modified
```
src/energy_usa/config.py                           (add TRANSFORM_DATABASE_URL)
src/energy_usa/db/__init__.py                      (rewrite exports)
src/energy_usa/db/dataframe.py                     (no changes needed)
src/energy_usa/db/period.py                        (no changes needed)
src/energy_usa/flows/__init__.py                   (rewrite exports)
src/energy_usa/flows/date_range.py                 (no changes needed)
docker/superset/seed_databases.py                  (update schema+table names)
scripts/deploy_ingest.py                           (update imports)
scripts/export_table.py                            (update default table name)
Makefile                                           (update TABLE default, add validate/audit)
dock.sh                                            (update ensure-ingest-db path)
compose.yaml                                       (no changes needed — volume mount stays the same)
.env.example                                       (add TRANSFORM_DATABASE_URL)
pyproject.toml                                     (add jinja2 dependency for generators)
CLAUDE.md
README.md
docs/README.md
docs/getting-started.md
docs/ingest-flows.md
docs/data-analysis.md
```

---

## Task 1: Docker Init SQL — Create Databases and New Init Script

This task consolidates the three separate database creation SQL files into one, creates the new directory structure for EIA tables, and writes a recursive init script.

**Files:**
- Create: `docker/postgres/init/01-create-databases.sql`
- Create: `docker/postgres/init/03-run-init-scripts.sh` (overwrite existing)
- Delete: `docker/postgres/init/02-create-ingest-db.sql`
- Delete: `docker/postgres/init/03-create-superset-db.sql`

- [ ] **Step 1: Write the consolidated database creation SQL**

```sql
-- docker/postgres/init/01-create-databases.sql
-- Create all application databases. Runs once on first container start.
-- Order: prefect (Prefect server metadata), ingest (EIA/EPA/FERC raw data),
-- transform (domain models), superset (BI dashboard metadata).

SELECT 'CREATE DATABASE prefect'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'prefect')\gexec

SELECT 'CREATE DATABASE ingest'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'ingest')\gexec

SELECT 'CREATE DATABASE transform'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'transform')\gexec

SELECT 'CREATE DATABASE superset'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'superset')\gexec
```

- [ ] **Step 2: Write the new recursive init script**

This replaces the current `03-run-ingest-schema.sh` which only walked flat `ingest/*.sql` files. The new script walks `ingest/` and `transform/` subdirectories recursively, running `00-*.sql` files first (schema creation), then remaining SQL files alphabetically.

```bash
#!/bin/bash
# docker/postgres/init/03-run-init-scripts.sh
# Run SQL files for the ingest and transform databases.
# Walks subdirectories recursively. Within each directory, 00-*.sql files run
# first (schema creation), then the rest in alphabetical order.
set -e

PG_USER="${POSTGRES_USER:-postgres}"
INIT_DIR="/docker-entrypoint-initdb.d"

run_sql_dir() {
  local db="$1"
  local dir="$2"
  [ -d "$dir" ] || return 0

  # Run 00-*.sql files first (schema setup)
  for f in "$dir"/00-*.sql; do
    [ -f "$f" ] || continue
    echo "  [$db] $f"
    psql -v ON_ERROR_STOP=1 -U "$PG_USER" -d "$db" -f "$f"
  done

  # Run remaining SQL files (skip 00-*)
  for f in "$dir"/*.sql; do
    [ -f "$f" ] || continue
    case "$(basename "$f")" in 00-*) continue ;; esac
    echo "  [$db] $f"
    psql -v ON_ERROR_STOP=1 -U "$PG_USER" -d "$db" -f "$f"
  done

  # Recurse into subdirectories
  for subdir in "$dir"/*/; do
    [ -d "$subdir" ] || continue
    run_sql_dir "$db" "$subdir"
  done
}

echo "=== Initializing ingest database ==="
run_sql_dir "ingest" "$INIT_DIR/ingest"

echo "=== Initializing transform database ==="
run_sql_dir "transform" "$INIT_DIR/transform"

echo "=== Database initialization complete ==="
```

- [ ] **Step 3: Delete old database creation files**

```bash
rm docker/postgres/init/02-create-ingest-db.sql
rm docker/postgres/init/03-create-superset-db.sql
rm docker/postgres/init/01-create-prefect-db.sql
```

The `01-create-databases.sql` replaces all three.

- [ ] **Step 4: Commit**

```bash
git add docker/postgres/init/01-create-databases.sql \
        docker/postgres/init/03-run-init-scripts.sh
git rm docker/postgres/init/02-create-ingest-db.sql \
       docker/postgres/init/03-create-superset-db.sql \
       docker/postgres/init/01-create-prefect-db.sql
git commit -m "$(cat <<'EOF'
consolidate database creation SQL and add recursive init script

Replaces three separate CREATE DATABASE files with one. The init script
now walks ingest/ and transform/ subdirectories recursively, running
00-*.sql (schema creation) first within each directory.
EOF
)"
```

---

## Task 2: Docker Init SQL — Reorganize EIA Schema Files

Move the 36 EIA table DDL files from flat `ingest/NN-<name>.sql` to `ingest/eia/<name>.sql`, create the `eia` schema SQL, update table references from `ingest.eia_*` to `eia.*`, and create the quality schema.

**Files:**
- Create: `docker/postgres/init/ingest/eia/00-schema.sql`
- Create: `docker/postgres/init/ingest/00-quality-schema.sql`
- Create: `docker/postgres/init/transform/00-create-schema-placeholder.sql`
- Move+Rename: 36 SQL files from `ingest/NN-<name>.sql` to `ingest/eia/<name>.sql`
- Delete: `docker/postgres/init/ingest/00-schema.sql` (old `CREATE SCHEMA ingest`)

- [ ] **Step 1: Create the eia schema SQL and quality schema SQL**

```sql
-- docker/postgres/init/ingest/eia/00-schema.sql
-- Create the eia schema for all EIA API datasets.
CREATE SCHEMA IF NOT EXISTS eia;
```

```sql
-- docker/postgres/init/ingest/00-quality-schema.sql
-- Quality audit schema for data validation results.
CREATE SCHEMA IF NOT EXISTS quality;

CREATE TABLE IF NOT EXISTS quality.audit_rules (
    rule_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    dataset TEXT NOT NULL,
    check_type TEXT NOT NULL,
    column_name TEXT,
    threshold JSONB NOT NULL,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS quality.audit_results (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    rule_id TEXT REFERENCES quality.audit_rules(rule_id),
    run_id TEXT NOT NULL,
    status TEXT NOT NULL,
    measured_value JSONB,
    detail TEXT,
    checked_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_results_rule
    ON quality.audit_results(rule_id, checked_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_results_run
    ON quality.audit_results(run_id);
```

```sql
-- docker/postgres/init/transform/00-create-schema-placeholder.sql
-- Placeholder: transform schemas will be added by Plan 4.
-- This file ensures the transform/ directory exists for the init script.
```

- [ ] **Step 2: Move and rename all 36 EIA SQL files**

Run this script from the repo root. It moves each file, strips the numeric prefix and `eia_` from table names, and does a find-replace of `ingest.eia_` → `eia.` and `ingest.ingest_` → `eia.` inside each file.

```bash
mkdir -p docker/postgres/init/ingest/eia

# Map of old filename → new filename
declare -A SQL_MOVES=(
  ["01-retail-sales.sql"]="retail_sales.sql"
  ["02-electric-power-operational.sql"]="electric_power_operational.sql"
  ["03-state-source-disposition.sql"]="state_source_disposition.sql"
  ["04-state-summary.sql"]="state_summary.sql"
  ["05-ingest-dataset-cadence.sql"]="dataset_cadence.sql"
  ["06-rto-region-data.sql"]="rto_region_data.sql"
  ["07-rto-fuel-type-data.sql"]="rto_fuel_type_data.sql"
  ["08-rto-region-sub-ba-data.sql"]="rto_region_sub_ba_data.sql"
  ["09-rto-interchange-data.sql"]="rto_interchange_data.sql"
  ["10-rto-daily-region-data.sql"]="rto_daily_region_data.sql"
  ["11-facility-fuel.sql"]="facility_fuel.sql"
  ["12-operating-generator-capacity.sql"]="operating_generator_capacity.sql"
  ["13-sep-emissions.sql"]="sep_emissions.sql"
  ["14-sep-capability.sql"]="sep_capability.sql"
  ["15-sep-net-metering.sql"]="sep_net_metering.sql"
  ["16-coal-aggregate-production.sql"]="coal_aggregate_production.sql"
  ["17-coal-consumption-quality.sql"]="coal_consumption_quality.sql"
  ["18-coal-mine-production.sql"]="coal_mine_production.sql"
  ["19-crude-oil-imports.sql"]="crude_oil_imports.sql"
  ["20-nuclear-outages-us.sql"]="nuclear_outages_us.sql"
  ["21-nuclear-outages-facility.sql"]="nuclear_outages_facility.sql"
  ["22-co2-emissions.sql"]="co2_emissions.sql"
  ["23-natural-gas-prices.sql"]="natural_gas_prices.sql"
  ["24-natural-gas-consumption.sql"]="natural_gas_consumption.sql"
  ["25-natural-gas-production.sql"]="natural_gas_production.sql"
  ["26-natural-gas-storage.sql"]="natural_gas_storage.sql"
  ["27-petroleum-prices.sql"]="petroleum_prices.sql"
  ["28-petroleum-supply.sql"]="petroleum_supply.sql"
  ["29-total-energy.sql"]="total_energy.sql"
  ["30-seds.sql"]="seds.sql"
  ["31-steo.sql"]="steo.sql"
  ["32-international.sql"]="international.sql"
  ["33-biomass-capacity.sql"]="biomass_capacity.sql"
  ["34-biomass-production.sql"]="biomass_production.sql"
  ["35-aeo.sql"]="aeo.sql"
  ["36-ieo.sql"]="ieo.sql"
)

for old_name in "${!SQL_MOVES[@]}"; do
  new_name="${SQL_MOVES[$old_name]}"
  src="docker/postgres/init/ingest/$old_name"
  dst="docker/postgres/init/ingest/eia/$new_name"
  if [ -f "$src" ]; then
    cp "$src" "$dst"
    # Replace schema references: ingest.eia_X → eia.X, ingest.ingest_X → eia.X
    sed -i '' 's/ingest\.eia_/eia./g' "$dst"
    sed -i '' 's/ingest\.ingest_/eia./g' "$dst"
    rm "$src"
  fi
done

# Remove old schema file
rm -f docker/postgres/init/ingest/00-schema.sql
```

- [ ] **Step 3: Verify the SQL files**

Spot-check a few renamed files to confirm the schema references are correct:

```bash
head -5 docker/postgres/init/ingest/eia/retail_sales.sql
# Expected: CREATE TABLE IF NOT EXISTS eia.retail_sales (
head -5 docker/postgres/init/ingest/eia/dataset_cadence.sql
# Expected: CREATE TABLE IF NOT EXISTS eia.dataset_cadence (
ls docker/postgres/init/ingest/eia/ | wc -l
# Expected: 37 (00-schema.sql + 36 table files)
```

- [ ] **Step 4: Commit**

```bash
git add docker/postgres/init/ingest/eia/ \
        docker/postgres/init/ingest/00-quality-schema.sql \
        docker/postgres/init/transform/
git rm docker/postgres/init/ingest/00-schema.sql \
       docker/postgres/init/ingest/01-retail-sales.sql \
       docker/postgres/init/ingest/02-electric-power-operational.sql \
       docker/postgres/init/ingest/03-state-source-disposition.sql \
       docker/postgres/init/ingest/04-state-summary.sql \
       docker/postgres/init/ingest/05-ingest-dataset-cadence.sql \
       docker/postgres/init/ingest/06-rto-region-data.sql \
       docker/postgres/init/ingest/07-rto-fuel-type-data.sql \
       docker/postgres/init/ingest/08-rto-region-sub-ba-data.sql \
       docker/postgres/init/ingest/09-rto-interchange-data.sql \
       docker/postgres/init/ingest/10-rto-daily-region-data.sql \
       docker/postgres/init/ingest/11-facility-fuel.sql \
       docker/postgres/init/ingest/12-operating-generator-capacity.sql \
       docker/postgres/init/ingest/13-sep-emissions.sql \
       docker/postgres/init/ingest/14-sep-capability.sql \
       docker/postgres/init/ingest/15-sep-net-metering.sql \
       docker/postgres/init/ingest/16-coal-aggregate-production.sql \
       docker/postgres/init/ingest/17-coal-consumption-quality.sql \
       docker/postgres/init/ingest/18-coal-mine-production.sql \
       docker/postgres/init/ingest/19-crude-oil-imports.sql \
       docker/postgres/init/ingest/20-nuclear-outages-us.sql \
       docker/postgres/init/ingest/21-nuclear-outages-facility.sql \
       docker/postgres/init/ingest/22-co2-emissions.sql \
       docker/postgres/init/ingest/23-natural-gas-prices.sql \
       docker/postgres/init/ingest/24-natural-gas-consumption.sql \
       docker/postgres/init/ingest/25-natural-gas-production.sql \
       docker/postgres/init/ingest/26-natural-gas-storage.sql \
       docker/postgres/init/ingest/27-petroleum-prices.sql \
       docker/postgres/init/ingest/28-petroleum-supply.sql \
       docker/postgres/init/ingest/29-total-energy.sql \
       docker/postgres/init/ingest/30-seds.sql \
       docker/postgres/init/ingest/31-steo.sql \
       docker/postgres/init/ingest/32-international.sql \
       docker/postgres/init/ingest/33-biomass-capacity.sql \
       docker/postgres/init/ingest/34-biomass-production.sql \
       docker/postgres/init/ingest/35-aeo.sql \
       docker/postgres/init/ingest/36-ieo.sql
git commit -m "$(cat <<'EOF'
reorganize init SQL: source-as-schema (eia.*) and quality schema

Moves 36 EIA table DDLs from ingest/NN-name.sql to ingest/eia/name.sql.
Tables renamed from ingest.eia_X to eia.X. Adds quality schema with
audit_rules and audit_results tables. Adds transform database placeholder.
EOF
)"
```

---

## Task 3: Create `clients/` Package

Move the EIA client and manager from `src/energy_usa/eia/` to `src/energy_usa/clients/`, add the `DataClient` protocol, and remove the old `eia/` directory.

**Files:**
- Create: `src/energy_usa/clients/__init__.py`
- Create: `src/energy_usa/clients/base.py`
- Create: `src/energy_usa/clients/eia.py` (consolidate client.py + manager.py)
- Delete: `src/energy_usa/eia/` (entire directory)

- [ ] **Step 1: Create `clients/base.py` with the DataClient protocol**

```python
# src/energy_usa/clients/base.py
"""Protocol defining the interface for data source API clients."""

from typing import Any, Protocol


class DataClient(Protocol):
    """Interface that all source API clients must satisfy.

    :param dataset: Dataset identifier (e.g. 'retail-sales/data').
    :param start: Start period (YYYY-MM or YYYY).
    :param end: End period (YYYY-MM or YYYY).
    :param columns: Data columns to request.
    :returns: List of row dicts from the API.
    """

    async def fetch_dataset(
        self, dataset: str, start: str, end: str, columns: list[str]
    ) -> list[dict[str, Any]]: ...

    async def aclose(self) -> None: ...
```

- [ ] **Step 2: Copy eia/client.py and eia/manager.py into clients/eia.py**

Read the current `eia/client.py` and `eia/manager.py` files. Combine them into a single `clients/eia.py` file. Keep both classes (`EIAClient` and `EIAManager`) with their existing logic unchanged. Update the internal import: `EIAManager` currently imports `EIAClient` from `energy_usa.eia.client` — change to a same-module reference since they're now in the same file.

The combined file structure:

```python
# src/energy_usa/clients/eia.py
"""EIA API client and call manager.

EIAClient: low-level async HTTP client with pagination.
EIAManager: production wrapper with concurrency semaphore and exponential backoff.
"""

# ... (full contents of client.py, then manager.py, with EIAManager's
#      import of EIAClient changed from cross-module to same-file reference)
```

Specifically, in the `EIAManager.__init__` method (or wherever `EIAClient` is instantiated), replace:
```python
from energy_usa.eia.client import EIAClient
```
with nothing — `EIAClient` is now defined above in the same file.

- [ ] **Step 3: Create `clients/__init__.py`**

```python
# src/energy_usa/clients/__init__.py
"""Data source API clients.

Each source (EIA, EPA, FERC) gets its own module. All clients satisfy
the DataClient protocol defined in base.py.
"""

from energy_usa.clients.base import DataClient
from energy_usa.clients.eia import EIAClient, EIAManager

__all__ = ["DataClient", "EIAClient", "EIAManager"]
```

- [ ] **Step 4: Delete the old `eia/` directory**

```bash
rm -rf src/energy_usa/eia/
```

- [ ] **Step 5: Verify imports work**

```bash
uv run python -c "from energy_usa.clients import EIAClient, EIAManager, DataClient; print('OK')"
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add src/energy_usa/clients/
git rm -r src/energy_usa/eia/
git commit -m "$(cat <<'EOF'
move EIA client to clients/ package with DataClient protocol

Consolidates eia/client.py and eia/manager.py into clients/eia.py.
Adds clients/base.py with DataClient protocol that all future source
clients will satisfy.
EOF
)"
```

---

## Task 4: Extract `db/connection.py` and Restructure DB Modules

Extract `get_connection()` from `db/retail_sales.py` into its own module, create the nested `db/ingest/eia/` package, move all 36 db modules there, and update SQL table references from `ingest.eia_*` to `eia.*`.

**Files:**
- Create: `src/energy_usa/db/connection.py`
- Create: `src/energy_usa/db/ingest/__init__.py`
- Create: `src/energy_usa/db/ingest/eia/__init__.py`
- Move: 36 db modules from `db/<name>.py` to `db/ingest/eia/<name>.py`
- Modify: Each moved file — change `ingest.eia_` to `eia.` in SQL strings
- Modify: `src/energy_usa/db/__init__.py` — rewrite exports
- Delete: 36 old db module files

- [ ] **Step 1: Create `db/connection.py`**

```python
# src/energy_usa/db/connection.py
"""Shared database connection helper for all layers."""

import psycopg
from psycopg.rows import dict_row


def get_connection(database_url: str) -> psycopg.Connection:
    """Open a sync connection to Postgres with dict row factory.

    :param database_url: PostgreSQL connection URL.
    :returns: An open connection; caller must close it.
    """
    return psycopg.connect(database_url, row_factory=dict_row)
```

- [ ] **Step 2: Move db modules and update table references**

Run this script from the repo root. For each db module:
1. Copy to new location
2. Replace `ingest.eia_` with `eia.` in SQL strings
3. Replace `ingest.ingest_` with `eia.` (for dataset_cadence)
4. Replace `from energy_usa.db.retail_sales import get_connection` with `from energy_usa.db.connection import get_connection` (only retail_sales.py exports this)
5. Remove the `get_connection` function definition from retail_sales.py (it now lives in connection.py)

```bash
mkdir -p src/energy_usa/db/ingest/eia

# List of all db module files to move (excludes period.py, dataframe.py, __init__.py, connection.py)
DB_MODULES=(
  aeo biomass_capacity biomass_production coal_aggregate_production
  coal_consumption_quality coal_mine_production co2_emissions crude_oil_imports
  electric_power_operational facility_fuel ieo international
  natural_gas_consumption natural_gas_prices natural_gas_production
  natural_gas_storage nuclear_outages_facility nuclear_outages_us
  operating_generator_capacity petroleum_prices petroleum_supply
  retail_sales rto_daily_region_data rto_fuel_type_data rto_interchange_data
  rto_region_data rto_region_sub_ba_data seds sep_capability sep_emissions
  sep_net_metering state_source_disposition state_summary steo total_energy
)

for mod in "${DB_MODULES[@]}"; do
  src="src/energy_usa/db/${mod}.py"
  dst="src/energy_usa/db/ingest/eia/${mod}.py"
  if [ -f "$src" ]; then
    cp "$src" "$dst"
    # Update SQL table references
    sed -i '' 's/ingest\.eia_/eia./g' "$dst"
    sed -i '' 's/ingest\.ingest_/eia./g' "$dst"
    # Update import of get_connection (only retail_sales.py defines it)
    sed -i '' 's/from energy_usa\.db\.retail_sales import get_connection/from energy_usa.db.connection import get_connection/g' "$dst"
    # Update import of period module
    sed -i '' 's/from energy_usa\.db\.period/from energy_usa.db.period/g' "$dst"
    rm "$src"
  fi
done
```

After the script, manually edit `db/ingest/eia/retail_sales.py` to:
1. Remove the `get_connection` function definition (lines 15-22 of original)
2. Remove the `from psycopg.rows import dict_row` import (no longer needed)
3. Add `from energy_usa.db.connection import get_connection` if the upsert function uses it internally (it doesn't — the connection is passed in)

The final `db/ingest/eia/retail_sales.py` should look like:

```python
"""Upsert EIA electricity retail-sales rows into Postgres.

Uses the eia.retail_sales table with unique (period, stateid, sectorid).
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period


def upsert_retail_sales(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA retail-sales rows into eia.retail_sales.

    :param conn: An open psycopg connection.
    :param rows: List of dicts with keys period, stateid, sectorid, and optionally
        revenue, sales, price, customers.
    :returns: Number of rows affected.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO eia.retail_sales (period, stateid, sectorid, revenue, sales, price, customers, ingested_at)
    VALUES (%(period)s, %(stateid)s, %(sectorid)s, %(revenue)s, %(sales)s, %(price)s, %(customers)s, now())
    ON CONFLICT (period, stateid, sectorid)
    DO UPDATE SET
        revenue = EXCLUDED.revenue,
        sales = EXCLUDED.sales,
        price = EXCLUDED.price,
        customers = EXCLUDED.customers,
        ingested_at = now()
    """
    normalized = []
    for r in rows:
        period_date = normalize_period(r.get("period"), "monthly")
        if period_date is None:
            continue
        normalized.append({
            "period": period_date,
            "stateid": r.get("stateid"),
            "sectorid": r.get("sectorid"),
            "revenue": r.get("revenue"),
            "sales": r.get("sales"),
            "price": r.get("price"),
            "customers": r.get("customers"),
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
```

- [ ] **Step 3: Create `__init__.py` files for the new packages**

```python
# src/energy_usa/db/ingest/__init__.py
"""Ingest database modules, organized by source."""
```

```python
# src/energy_usa/db/ingest/eia/__init__.py
"""EIA ingest database modules — one upsert function per dataset."""

from energy_usa.db.ingest.eia.aeo import upsert_aeo
from energy_usa.db.ingest.eia.biomass_capacity import upsert_biomass_capacity
from energy_usa.db.ingest.eia.biomass_production import upsert_biomass_production
from energy_usa.db.ingest.eia.coal_aggregate_production import upsert_coal_aggregate_production
from energy_usa.db.ingest.eia.coal_consumption_quality import upsert_coal_consumption_quality
from energy_usa.db.ingest.eia.coal_mine_production import upsert_coal_mine_production
from energy_usa.db.ingest.eia.co2_emissions import upsert_co2_emissions
from energy_usa.db.ingest.eia.crude_oil_imports import upsert_crude_oil_imports
from energy_usa.db.ingest.eia.electric_power_operational import upsert_electric_power_operational
from energy_usa.db.ingest.eia.facility_fuel import upsert_facility_fuel
from energy_usa.db.ingest.eia.ieo import upsert_ieo
from energy_usa.db.ingest.eia.international import upsert_international
from energy_usa.db.ingest.eia.natural_gas_consumption import upsert_natural_gas_consumption
from energy_usa.db.ingest.eia.natural_gas_prices import upsert_natural_gas_prices
from energy_usa.db.ingest.eia.natural_gas_production import upsert_natural_gas_production
from energy_usa.db.ingest.eia.natural_gas_storage import upsert_natural_gas_storage
from energy_usa.db.ingest.eia.nuclear_outages_facility import upsert_nuclear_outages_facility
from energy_usa.db.ingest.eia.nuclear_outages_us import upsert_nuclear_outages_us
from energy_usa.db.ingest.eia.operating_generator_capacity import upsert_operating_generator_capacity
from energy_usa.db.ingest.eia.petroleum_prices import upsert_petroleum_prices
from energy_usa.db.ingest.eia.petroleum_supply import upsert_petroleum_supply
from energy_usa.db.ingest.eia.retail_sales import upsert_retail_sales
from energy_usa.db.ingest.eia.rto_daily_region_data import upsert_rto_daily_region_data
from energy_usa.db.ingest.eia.rto_fuel_type_data import upsert_rto_fuel_type_data
from energy_usa.db.ingest.eia.rto_interchange_data import upsert_rto_interchange_data
from energy_usa.db.ingest.eia.rto_region_data import upsert_rto_region_data
from energy_usa.db.ingest.eia.rto_region_sub_ba_data import upsert_rto_region_sub_ba_data
from energy_usa.db.ingest.eia.seds import upsert_seds
from energy_usa.db.ingest.eia.sep_capability import upsert_sep_capability
from energy_usa.db.ingest.eia.sep_emissions import upsert_sep_emissions
from energy_usa.db.ingest.eia.sep_net_metering import upsert_sep_net_metering
from energy_usa.db.ingest.eia.state_source_disposition import upsert_state_source_disposition
from energy_usa.db.ingest.eia.state_summary import upsert_state_summary
from energy_usa.db.ingest.eia.steo import upsert_steo
from energy_usa.db.ingest.eia.total_energy import upsert_total_energy

__all__ = [
    "upsert_aeo",
    "upsert_biomass_capacity",
    "upsert_biomass_production",
    "upsert_coal_aggregate_production",
    "upsert_coal_consumption_quality",
    "upsert_coal_mine_production",
    "upsert_co2_emissions",
    "upsert_crude_oil_imports",
    "upsert_electric_power_operational",
    "upsert_facility_fuel",
    "upsert_ieo",
    "upsert_international",
    "upsert_natural_gas_consumption",
    "upsert_natural_gas_prices",
    "upsert_natural_gas_production",
    "upsert_natural_gas_storage",
    "upsert_nuclear_outages_facility",
    "upsert_nuclear_outages_us",
    "upsert_operating_generator_capacity",
    "upsert_petroleum_prices",
    "upsert_petroleum_supply",
    "upsert_retail_sales",
    "upsert_rto_daily_region_data",
    "upsert_rto_fuel_type_data",
    "upsert_rto_interchange_data",
    "upsert_rto_region_data",
    "upsert_rto_region_sub_ba_data",
    "upsert_seds",
    "upsert_sep_capability",
    "upsert_sep_emissions",
    "upsert_sep_net_metering",
    "upsert_state_source_disposition",
    "upsert_state_summary",
    "upsert_steo",
    "upsert_total_energy",
]
```

- [ ] **Step 4: Rewrite `db/__init__.py`**

```python
# src/energy_usa/db/__init__.py
"""Database layer — connection helpers, period normalization, and ingest upserts.

Subpackages:
- db.ingest.eia — EIA upsert functions (one per dataset)
- db.connection — shared get_connection() helper
- db.period — period normalization utilities
- db.dataframe — SQL-to-DataFrame helper
"""

from energy_usa.db.connection import get_connection
from energy_usa.db.dataframe import query_to_dataframe
from energy_usa.db.ingest.eia import *  # noqa: F401,F403 — re-exports all upsert functions

__all__ = [
    "get_connection",
    "query_to_dataframe",
]
```

Note: The wildcard re-export preserves backward compatibility for any code that does `from energy_usa.db import upsert_retail_sales`. This is a transitional measure — Plan 2 (generators) will update all consumers to use the direct path.

- [ ] **Step 5: Verify imports work**

```bash
uv run python -c "
from energy_usa.db.connection import get_connection
from energy_usa.db.ingest.eia.retail_sales import upsert_retail_sales
from energy_usa.db.ingest.eia.co2_emissions import upsert_co2_emissions
from energy_usa.db import get_connection, upsert_retail_sales
print('All imports OK')
"
```

Expected: `All imports OK`

- [ ] **Step 6: Commit**

```bash
git add src/energy_usa/db/connection.py \
        src/energy_usa/db/ingest/ \
        src/energy_usa/db/__init__.py
git rm src/energy_usa/db/aeo.py \
       src/energy_usa/db/biomass_capacity.py \
       src/energy_usa/db/biomass_production.py \
       src/energy_usa/db/coal_aggregate_production.py \
       src/energy_usa/db/coal_consumption_quality.py \
       src/energy_usa/db/coal_mine_production.py \
       src/energy_usa/db/co2_emissions.py \
       src/energy_usa/db/crude_oil_imports.py \
       src/energy_usa/db/electric_power_operational.py \
       src/energy_usa/db/facility_fuel.py \
       src/energy_usa/db/ieo.py \
       src/energy_usa/db/international.py \
       src/energy_usa/db/natural_gas_consumption.py \
       src/energy_usa/db/natural_gas_prices.py \
       src/energy_usa/db/natural_gas_production.py \
       src/energy_usa/db/natural_gas_storage.py \
       src/energy_usa/db/nuclear_outages_facility.py \
       src/energy_usa/db/nuclear_outages_us.py \
       src/energy_usa/db/operating_generator_capacity.py \
       src/energy_usa/db/petroleum_prices.py \
       src/energy_usa/db/petroleum_supply.py \
       src/energy_usa/db/retail_sales.py \
       src/energy_usa/db/rto_daily_region_data.py \
       src/energy_usa/db/rto_fuel_type_data.py \
       src/energy_usa/db/rto_interchange_data.py \
       src/energy_usa/db/rto_region_data.py \
       src/energy_usa/db/rto_region_sub_ba_data.py \
       src/energy_usa/db/seds.py \
       src/energy_usa/db/sep_capability.py \
       src/energy_usa/db/sep_emissions.py \
       src/energy_usa/db/sep_net_metering.py \
       src/energy_usa/db/state_source_disposition.py \
       src/energy_usa/db/state_summary.py \
       src/energy_usa/db/steo.py \
       src/energy_usa/db/total_energy.py
git commit -m "$(cat <<'EOF'
move db modules to db/ingest/eia/, update table refs to eia.* schema

Extracts get_connection() into db/connection.py. Moves all 36 EIA upsert
modules to db/ingest/eia/ with SQL references updated from ingest.eia_X
to eia.X. Backward-compatible re-exports via db/__init__.py.
EOF
)"
```

---

## Task 5: Restructure Flow Modules

Move all 36 flow modules from `flows/eia_<name>.py` to `flows/ingest/eia/<name>.py`, update their imports to use the new db and client paths, and rewrite the backfill flow with dynamic discovery.

**Files:**
- Create: `src/energy_usa/flows/ingest/__init__.py`
- Create: `src/energy_usa/flows/ingest/eia/__init__.py`
- Create: `src/energy_usa/flows/ingest/backfill.py`
- Move: 36 flow files from `flows/eia_<name>.py` to `flows/ingest/eia/<name>.py`
- Modify: Each moved file — update db and client imports
- Modify: `src/energy_usa/flows/__init__.py` — rewrite exports
- Delete: `src/energy_usa/flows/backfill_eia.py`
- Delete: 36 old flow files

- [ ] **Step 1: Move flow modules and update imports**

```bash
mkdir -p src/energy_usa/flows/ingest/eia

# All flow modules (strip eia_ prefix for new filename)
FLOW_MODULES=(
  aeo biomass_capacity biomass_production coal_aggregate_production
  coal_consumption_quality coal_mine_production co2_emissions crude_oil_imports
  electric_power_operational facility_fuel ieo international
  natural_gas_consumption natural_gas_prices natural_gas_production
  natural_gas_storage nuclear_outages_facility nuclear_outages_us
  operating_generator_capacity petroleum_prices petroleum_supply
  retail_sales rto_daily_region_data rto_fuel_type_data rto_interchange_data
  rto_region_data rto_region_sub_ba_data seds sep_capability sep_emissions
  sep_net_metering state_source_disposition state_summary steo total_energy
)

for mod in "${FLOW_MODULES[@]}"; do
  src="src/energy_usa/flows/eia_${mod}.py"
  dst="src/energy_usa/flows/ingest/eia/${mod}.py"
  if [ -f "$src" ]; then
    cp "$src" "$dst"
    # Update db imports: from energy_usa.db import X → from energy_usa.db.ingest.eia.X import X
    # Update db imports: from energy_usa.db.X import upsert_X → from energy_usa.db.ingest.eia.X import upsert_X
    sed -i '' "s/from energy_usa\.db import get_connection, upsert_${mod}/from energy_usa.db.connection import get_connection\nfrom energy_usa.db.ingest.eia.${mod} import upsert_${mod}/g" "$dst"
    sed -i '' "s/from energy_usa\.db import upsert_${mod}/from energy_usa.db.ingest.eia.${mod} import upsert_${mod}/g" "$dst"
    sed -i '' "s/from energy_usa\.db\.${mod} import upsert_${mod}/from energy_usa.db.ingest.eia.${mod} import upsert_${mod}/g" "$dst"
    sed -i '' "s/from energy_usa\.db import get_connection/from energy_usa.db.connection import get_connection/g" "$dst"
    # Update client imports
    sed -i '' 's/from energy_usa\.eia\.manager import EIAManager/from energy_usa.clients.eia import EIAManager/g' "$dst"
    sed -i '' 's/from energy_usa\.eia import EIAManager/from energy_usa.clients.eia import EIAManager/g' "$dst"
    rm "$src"
  fi
done
```

After the bulk script, manually verify one representative file (`flows/ingest/eia/retail_sales.py`) to confirm:
- `from energy_usa.clients.eia import EIAManager` (was `energy_usa.eia.manager`)
- `from energy_usa.db.connection import get_connection` (was `energy_usa.db`)
- `from energy_usa.db.ingest.eia.retail_sales import upsert_retail_sales` (was `energy_usa.db`)
- `from energy_usa.flows.date_range import ...` (unchanged — date_range stays put)

- [ ] **Step 2: Write the dynamic backfill flow**

```python
# src/energy_usa/flows/ingest/backfill.py
"""Prefect flow to backfill datasets in configurable month chunks.

Dynamically discovers ingest flows by source name. The parent flow splits
a date range into chunks and submits one child flow per chunk.
"""

import asyncio
import importlib
import pkgutil
from typing import Any, Awaitable, Callable, Literal

from prefect import flow
from prefect.logging import get_run_logger

from energy_usa.flows.date_range import make_run_name, monthly_chunks, resolve_date_range

IngestFlow = Callable[..., Awaitable[int]]


def get_flow_registry(source: str) -> dict[str, IngestFlow]:
    """Discover all ingest flows for a source by importing its package.

    Looks for functions named ``ingest_<source>_<dataset>`` in each module
    under ``energy_usa.flows.ingest.<source>``.

    :param source: Source name (e.g. 'eia').
    :returns: Dict mapping dataset name to flow function.
    """
    registry: dict[str, IngestFlow] = {}
    package_name = f"energy_usa.flows.ingest.{source}"
    try:
        package = importlib.import_module(package_name)
    except ModuleNotFoundError:
        return registry

    prefix = f"ingest_{source}_"
    for _importer, module_name, _is_pkg in pkgutil.iter_modules(package.__path__):
        mod = importlib.import_module(f"{package_name}.{module_name}")
        for attr_name in dir(mod):
            if attr_name.startswith(prefix):
                dataset_name = attr_name[len(prefix):]
                fn = getattr(mod, attr_name)
                if callable(fn):
                    registry[dataset_name] = fn
    return registry


# Discover EIA datasets at import time for the Literal type
_EIA_REGISTRY = get_flow_registry("eia")
DatasetName = Literal[tuple(["all"] + sorted(_EIA_REGISTRY.keys()))]  # type: ignore[valid-type]


def _run_name(**kwargs: Any) -> str:
    ds = kwargs.get("dataset", "all")
    start = kwargs.get("date_start")
    end = kwargs.get("date_end")
    base = make_run_name("monthly", start, end)
    return f"{base} [{ds}]"


@flow(
    name="backfill-eia",
    flow_run_name=_run_name,
    timeout_seconds=86400,
)
async def backfill_eia(
    date_start: str | None = None,
    date_end: str | None = None,
    chunk_months: int = 1,
    dataset: DatasetName = "retail_sales",
) -> None:
    """Backfill one or all EIA datasets over a date range in monthly chunks.

    :param date_start: Start period (YYYY-MM). Defaults to last month.
    :param date_end: End period (YYYY-MM). Defaults to current month.
    :param chunk_months: Months per chunk (default 1).
    :param dataset: Dataset key or 'all'.
    """
    logger = get_run_logger()
    registry = get_flow_registry("eia")

    if dataset == "all":
        targets = list(registry.items())
    else:
        if dataset not in registry:
            raise ValueError(f"Unknown dataset '{dataset}'. Available: {sorted(registry.keys())}")
        targets = [(dataset, registry[dataset])]

    start, end = resolve_date_range(date_start, date_end)
    chunks = monthly_chunks(start, end, chunk_months)
    logger.info(
        "Backfill: %d dataset(s), %d chunk(s), range %s→%s",
        len(targets), len(chunks), start, end,
    )

    for ds_name, ds_flow in targets:
        for chunk_start, chunk_end in chunks:
            logger.info("Running %s: %s→%s", ds_name, chunk_start, chunk_end)
            await ds_flow(date_start=chunk_start, date_end=chunk_end)
```

- [ ] **Step 3: Create `__init__.py` files**

```python
# src/energy_usa/flows/ingest/__init__.py
"""Ingest flows, organized by source."""

from energy_usa.flows.ingest.backfill import backfill_eia

__all__ = ["backfill_eia"]
```

```python
# src/energy_usa/flows/ingest/eia/__init__.py
"""EIA ingest flows — one flow per dataset."""
```

- [ ] **Step 4: Rewrite `flows/__init__.py`**

```python
# src/energy_usa/flows/__init__.py
"""Prefect flows for scheduled ingest, validation, and transform jobs."""

from energy_usa.flows.ingest.backfill import backfill_eia

__all__ = ["backfill_eia"]
```

- [ ] **Step 5: Delete old flow files**

```bash
rm src/energy_usa/flows/backfill_eia.py
# The 36 eia_*.py files were already removed by the move script in Step 1
```

- [ ] **Step 6: Verify imports work**

```bash
uv run python -c "
from energy_usa.flows.ingest.eia.retail_sales import ingest_eia_retail_sales
from energy_usa.flows.ingest.backfill import backfill_eia, get_flow_registry
registry = get_flow_registry('eia')
print(f'Discovered {len(registry)} EIA flows')
assert len(registry) == 36, f'Expected 36, got {len(registry)}'
print('All flow imports OK')
"
```

Expected: `Discovered 36 EIA flows` and `All flow imports OK`

- [ ] **Step 7: Commit**

```bash
git add src/energy_usa/flows/ingest/ \
        src/energy_usa/flows/__init__.py
git rm src/energy_usa/flows/backfill_eia.py
git commit -m "$(cat <<'EOF'
move flows to flows/ingest/eia/, add dynamic backfill discovery

Moves 36 EIA flow modules to flows/ingest/eia/ with updated db and client
imports. Replaces hardcoded _FLOW_REGISTRY with dynamic discovery via
pkgutil. New datasets are automatically available for backfill.
EOF
)"
```

---

## Task 6: Update Config, Deploy Script, Superset Seed, and Makefile

Update all peripheral files that reference the old import paths or table names.

**Files:**
- Modify: `src/energy_usa/config.py`
- Modify: `scripts/deploy_ingest.py`
- Modify: `docker/superset/seed_databases.py`
- Modify: `scripts/export_table.py`
- Modify: `Makefile`
- Modify: `dock.sh`
- Modify: `.env.example`
- Modify: `pyproject.toml`

- [ ] **Step 1: Add `TRANSFORM_DATABASE_URL` to config.py**

Add after the `ingest_database_url` field in `src/energy_usa/config.py`:

```python
    transform_database_url: str = ""
    """PostgreSQL connection URL for the transform database.
    Example: postgresql://user:password@host:5432/transform. Empty means transform features are disabled."""
```

- [ ] **Step 2: Update `.env.example`**

Add after the `INGEST_DATABASE_URL` line:

```
# Transform domain models (cross-source joins, aggregations).
TRANSFORM_DATABASE_URL=postgresql://energy:energy@localhost:5432/transform
```

- [ ] **Step 3: Rewrite `scripts/deploy_ingest.py`**

Replace the 40 individual flow imports with dynamic discovery:

```python
#!/usr/bin/env -S uv run python
"""Register EIA ingest flows as Prefect deployments.

Discovers flows dynamically from the flows.ingest.eia package.
Run once after the Prefect server and worker are up.
"""
import asyncio

from prefect.deployments.runner import EntrypointType, RunnerDeployment

from energy_usa.flows.ingest.backfill import backfill_eia, get_flow_registry

# Cron schedules
MONTHLY_CRON = "0 0 1 * *"
QUARTERLY_CRON = "0 0 1 1,4,7,10 *"
ANNUAL_CRON = "0 0 2 1 *"
DAILY_CRON = "0 6 * * *"

# Map dataset names to their run schedule. Datasets not listed here default to MONTHLY_CRON.
SCHEDULE_OVERRIDES: dict[str, str] = {
    "rto_region_data": DAILY_CRON,
    "rto_fuel_type_data": DAILY_CRON,
    "rto_region_sub_ba_data": DAILY_CRON,
    "rto_interchange_data": DAILY_CRON,
    "rto_daily_region_data": DAILY_CRON,
    "nuclear_outages_us": DAILY_CRON,
    "nuclear_outages_facility": DAILY_CRON,
    "facility_fuel": ANNUAL_CRON,
    "operating_generator_capacity": ANNUAL_CRON,
    "sep_emissions": ANNUAL_CRON,
    "sep_capability": ANNUAL_CRON,
    "sep_net_metering": ANNUAL_CRON,
    "coal_aggregate_production": QUARTERLY_CRON,
    "coal_consumption_quality": QUARTERLY_CRON,
    "coal_mine_production": QUARTERLY_CRON,
    "co2_emissions": ANNUAL_CRON,
    "seds": ANNUAL_CRON,
    "international": ANNUAL_CRON,
    "biomass_capacity": ANNUAL_CRON,
    "biomass_production": ANNUAL_CRON,
    "aeo": ANNUAL_CRON,
    "ieo": ANNUAL_CRON,
}


async def main() -> None:
    registry = get_flow_registry("eia")
    deployments = []

    for dataset_name, flow_fn in sorted(registry.items()):
        cron = SCHEDULE_OVERRIDES.get(dataset_name, MONTHLY_CRON)
        name = f"ingest-eia-{dataset_name.replace('_', '-')}"
        deployments.append(
            RunnerDeployment.from_flow(
                flow_fn,
                name=name,
                work_pool_name="process-pool",
                cron=cron,
                tags=["ingest", "eia"],
                entrypoint_type=EntrypointType.MODULE_PATH,
            )
        )

    deployments.append(
        RunnerDeployment.from_flow(
            backfill_eia,
            name="backfill-eia",
            work_pool_name="process-pool",
            parameters={
                "date_start": None,
                "date_end": None,
                "chunk_months": 1,
                "dataset": "retail_sales",
            },
            tags=["backfill", "eia"],
            entrypoint_type=EntrypointType.MODULE_PATH,
        ),
    )

    for deployment in deployments:
        await deployment.apply()
    print(
        f"Deployments applied: {len(deployments)} total "
        f"({len(deployments) - 1} ingest + 1 backfill)."
    )


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 4: Update `docker/superset/seed_databases.py`**

Change all `("ingest", "eia_X")` tuples to `("eia", "X")`:

```python
DATASETS = [
    ("eia", "retail_sales"),
    ("eia", "electric_power_operational"),
    ("eia", "state_source_disposition"),
    ("eia", "state_summary"),
    ("eia", "dataset_cadence"),
    ("eia", "rto_region_data"),
    ("eia", "rto_fuel_type_data"),
    ("eia", "rto_region_sub_ba_data"),
    ("eia", "rto_interchange_data"),
    ("eia", "rto_daily_region_data"),
    ("eia", "facility_fuel"),
    ("eia", "operating_generator_capacity"),
    ("eia", "sep_emissions"),
    ("eia", "sep_capability"),
    ("eia", "sep_net_metering"),
    ("eia", "coal_aggregate_production"),
    ("eia", "coal_consumption_quality"),
    ("eia", "coal_mine_production"),
    ("eia", "crude_oil_imports"),
    ("eia", "nuclear_outages_us"),
    ("eia", "nuclear_outages_facility"),
    ("eia", "co2_emissions"),
    ("eia", "natural_gas_prices"),
    ("eia", "natural_gas_consumption"),
    ("eia", "natural_gas_production"),
    ("eia", "natural_gas_storage"),
    ("eia", "petroleum_prices"),
    ("eia", "petroleum_supply"),
    ("eia", "total_energy"),
    ("eia", "seds"),
    ("eia", "steo"),
    ("eia", "international"),
    ("eia", "biomass_capacity"),
    ("eia", "biomass_production"),
    ("eia", "aeo"),
    ("eia", "ieo"),
]
```

- [ ] **Step 5: Update `Makefile` default TABLE variable**

Change the default TABLE from `eia_retail_sales` to `eia.retail_sales`:

```makefile
TABLE     ?= eia.retail_sales       # Table for `make export` (schema.table format)
```

- [ ] **Step 6: Update `dock.sh` ensure-ingest-db command**

Update `cmd_ensure_ingest_db` to walk subdirectories:

```bash
cmd_ensure_ingest_db() {
  echo "Creating ingest database and tables (idempotent)..."
  $COMPOSE_CMD exec postgres bash -c '
    export PGPASSWORD="$POSTGRES_PASSWORD"
    psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE ingest;" 2>/dev/null || true
    psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE transform;" 2>/dev/null || true
    find /docker-entrypoint-initdb.d/ingest -name "*.sql" | sort | while read f; do
      psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d ingest -f "$f"
    done
    echo "Ingest database ready."
  '
}
```

- [ ] **Step 7: Add `jinja2` to pyproject.toml dependencies**

Add to the `dependencies` list in `pyproject.toml` (needed by generators in Plan 2):

```toml
    "jinja2>=3.1",
```

- [ ] **Step 8: Verify deploy script works**

```bash
uv run python -c "
from scripts.deploy_ingest import main
# Just verify imports work, don't actually deploy
print('Deploy script imports OK')
"
```

This will fail because `scripts/` isn't a package. Instead verify:

```bash
uv run python scripts/deploy_ingest.py --help 2>&1 || uv run python -c "
import importlib.util, sys
spec = importlib.util.spec_from_file_location('deploy', 'scripts/deploy_ingest.py')
mod = importlib.util.module_from_spec(spec)
# Don't execute main, just verify the module loads
print('Deploy script loads OK')
"
```

- [ ] **Step 9: Commit**

```bash
git add src/energy_usa/config.py \
        scripts/deploy_ingest.py \
        docker/superset/seed_databases.py \
        Makefile \
        dock.sh \
        .env.example \
        pyproject.toml
git commit -m "$(cat <<'EOF'
update config, deploy, superset seed, and Makefile for eia.* schema

Adds TRANSFORM_DATABASE_URL to config and .env.example. Rewrites deploy
script to use dynamic flow discovery. Updates Superset seed to eia.*
schema names. Updates Makefile TABLE default. Adds jinja2 dependency.
EOF
)"
```

---

## Task 7: Create Migration Script for Existing Deployments

Write a SQL migration that renames tables in-place for existing databases (Docker and Proxmox production).

**Files:**
- Create: `deploy/migrations/001-rename-eia-schemas.sql`

- [ ] **Step 1: Write the migration SQL**

```sql
-- deploy/migrations/001-rename-eia-schemas.sql
-- One-time migration: move tables from ingest.eia_* to eia.* schema.
-- Run against the ingest database:
--   psql -U energy -d ingest -f deploy/migrations/001-rename-eia-schemas.sql
--
-- Safe to run multiple times (IF NOT EXISTS / IF EXISTS guards).

BEGIN;

-- Create the eia schema
CREATE SCHEMA IF NOT EXISTS eia;

-- Create the quality schema
CREATE SCHEMA IF NOT EXISTS quality;

-- Move and rename each table
DO $$
DECLARE
    tbl TEXT;
    old_name TEXT;
    new_name TEXT;
    tables TEXT[] := ARRAY[
        'retail_sales', 'electric_power_operational', 'state_source_disposition',
        'state_summary', 'rto_region_data', 'rto_fuel_type_data',
        'rto_region_sub_ba_data', 'rto_interchange_data', 'rto_daily_region_data',
        'facility_fuel', 'operating_generator_capacity', 'sep_emissions',
        'sep_capability', 'sep_net_metering', 'coal_aggregate_production',
        'coal_consumption_quality', 'coal_mine_production', 'crude_oil_imports',
        'nuclear_outages_us', 'nuclear_outages_facility', 'co2_emissions',
        'natural_gas_prices', 'natural_gas_consumption', 'natural_gas_production',
        'natural_gas_storage', 'petroleum_prices', 'petroleum_supply',
        'total_energy', 'seds', 'steo', 'international',
        'biomass_capacity', 'biomass_production', 'aeo', 'ieo'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables LOOP
        old_name := 'ingest.eia_' || tbl;
        new_name := tbl;
        -- Move to eia schema, then rename to strip prefix
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'ingest' AND table_name = 'eia_' || tbl) THEN
            EXECUTE format('ALTER TABLE %s SET SCHEMA eia', old_name);
            EXECUTE format('ALTER TABLE eia.eia_%s RENAME TO %s', tbl, new_name);
            RAISE NOTICE 'Migrated: ingest.eia_% → eia.%', tbl, tbl;
        END IF;
    END LOOP;

    -- Handle ingest_dataset_cadence → eia.dataset_cadence
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'ingest' AND table_name = 'ingest_dataset_cadence') THEN
        ALTER TABLE ingest.ingest_dataset_cadence SET SCHEMA eia;
        ALTER TABLE eia.ingest_dataset_cadence RENAME TO dataset_cadence;
        RAISE NOTICE 'Migrated: ingest.ingest_dataset_cadence → eia.dataset_cadence';
    END IF;
END $$;

-- Create quality tables (same as 00-quality-schema.sql)
CREATE TABLE IF NOT EXISTS quality.audit_rules (
    rule_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    dataset TEXT NOT NULL,
    check_type TEXT NOT NULL,
    column_name TEXT,
    threshold JSONB NOT NULL,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS quality.audit_results (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    rule_id TEXT REFERENCES quality.audit_rules(rule_id),
    run_id TEXT NOT NULL,
    status TEXT NOT NULL,
    measured_value JSONB,
    detail TEXT,
    checked_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_results_rule
    ON quality.audit_results(rule_id, checked_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_results_run
    ON quality.audit_results(run_id);

-- Create transform database (must be run separately as superuser against postgres db)
-- SELECT 'CREATE DATABASE transform' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'transform')\gexec

-- Drop old ingest schema if empty
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'ingest') THEN
        DROP SCHEMA IF EXISTS ingest;
        RAISE NOTICE 'Dropped empty ingest schema';
    ELSE
        RAISE NOTICE 'ingest schema still has tables — not dropping';
    END IF;
END $$;

COMMIT;
```

- [ ] **Step 2: Commit**

```bash
mkdir -p deploy/migrations
git add deploy/migrations/001-rename-eia-schemas.sql
git commit -m "$(cat <<'EOF'
add migration script for existing deployments (ingest.eia_* → eia.*)

Idempotent SQL that moves all 36 EIA tables from the ingest schema to
the eia schema and strips the eia_ prefix. Creates quality schema.
Safe to run multiple times.
EOF
)"
```

---

## Task 8: Update Tests

Move test files to mirror the new package structure and update table/import references.

**Files:**
- Create: `tests/unit/db/__init__.py`, `tests/unit/db/ingest/__init__.py`, `tests/unit/db/ingest/eia/__init__.py`
- Create: `tests/integration/db/__init__.py`, `tests/integration/db/ingest/__init__.py`, `tests/integration/db/ingest/eia/__init__.py`
- Move: `tests/unit/test_upsert_normalization.py` → `tests/unit/db/ingest/eia/test_upsert_normalization.py`
- Move: `tests/integration/test_db_upserts.py` → `tests/integration/db/ingest/eia/test_db_upserts.py`
- Modify: Both test files — update imports and SQL references

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p tests/unit/db/ingest/eia
mkdir -p tests/integration/db/ingest/eia
touch tests/unit/db/__init__.py
touch tests/unit/db/ingest/__init__.py
touch tests/unit/db/ingest/eia/__init__.py
touch tests/integration/db/__init__.py
touch tests/integration/db/ingest/__init__.py
touch tests/integration/db/ingest/eia/__init__.py
```

- [ ] **Step 2: Move and update unit test file**

```bash
mv tests/unit/test_upsert_normalization.py tests/unit/db/ingest/eia/test_upsert_normalization.py
```

Update imports in `tests/unit/db/ingest/eia/test_upsert_normalization.py`:

```python
# Old:
from energy_usa.db.retail_sales import upsert_retail_sales
from energy_usa.db.electric_power_operational import upsert_electric_power_operational
from energy_usa.db.state_summary import upsert_state_summary

# New:
from energy_usa.db.ingest.eia.retail_sales import upsert_retail_sales
from energy_usa.db.ingest.eia.electric_power_operational import upsert_electric_power_operational
from energy_usa.db.ingest.eia.state_summary import upsert_state_summary
```

- [ ] **Step 3: Move and update integration test file**

```bash
mv tests/integration/test_db_upserts.py tests/integration/db/ingest/eia/test_db_upserts.py
```

Update imports in `tests/integration/db/ingest/eia/test_db_upserts.py`:

```python
# Old:
from energy_usa.db.retail_sales import upsert_retail_sales
from energy_usa.db.electric_power_operational import upsert_electric_power_operational
from energy_usa.db.state_summary import upsert_state_summary

# New:
from energy_usa.db.ingest.eia.retail_sales import upsert_retail_sales
from energy_usa.db.ingest.eia.electric_power_operational import upsert_electric_power_operational
from energy_usa.db.ingest.eia.state_summary import upsert_state_summary
```

Also update any SQL query strings in the integration tests that reference `ingest.eia_*`:

```python
# Old:
cur.execute("SELECT price FROM ingest.eia_retail_sales WHERE ...")

# New:
cur.execute("SELECT price FROM eia.retail_sales WHERE ...")
```

Apply this pattern to all SQL strings in the file.

- [ ] **Step 4: Run unit tests**

```bash
uv run pytest tests/unit/ -v
```

Expected: All tests pass. The period and date_range tests are unaffected. The upsert normalization tests use mock connections so they don't hit the DB — they should pass as long as imports resolve.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/db/ tests/integration/db/
git rm tests/unit/test_upsert_normalization.py tests/integration/test_db_upserts.py
git commit -m "$(cat <<'EOF'
move tests to mirror new db/ingest/eia/ package structure

Updates imports to new paths and SQL references to eia.* schema.
EOF
)"
```

---

## Task 9: Update Documentation

Update all docs to reflect the new architecture: schema names, package paths, commands, and data flow.

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`
- Modify: `docs/README.md`
- Modify: `docs/getting-started.md`
- Modify: `docs/ingest-flows.md`
- Modify: `docs/data-analysis.md`

- [ ] **Step 1: Update CLAUDE.md**

Key changes throughout the file:

1. **Data Flow diagram**: Update to show the layered pipeline:
```
EIA API → EIAClient → EIAManager → Prefect Flow → Postgres (eia.* schema)
                                                        ↓
                                              Validation Flows → quality.*
                                                        ↓
                                              Transform Flows → transform DB
                                                        ↓
                                                Superset Dashboard
```

2. **Key Components section**: Update paths:
   - `eia/client.py` → `clients/eia.py`
   - `eia/manager.py` → consolidated into `clients/eia.py`
   - `db/` description → `db/ingest/eia/` with note about `db/connection.py`
   - `flows/` description → `flows/ingest/eia/`
   - Add: `clients/base.py` — DataClient protocol
   - Add: `generators/` — (coming in Plan 2)

3. **Databases table**: Add transform database:

| Database | Connection var | Purpose |
|----------|---------------|---------|
| `ingest` | `INGEST_DATABASE_URL` | EIA raw data (eia.* schema), quality audits (quality.* schema) |
| `transform` | `TRANSFORM_DATABASE_URL` | Domain models (electricity.*, fossil_fuels.*, etc.) |

4. **Ingest Patterns section**: Update table references from `ingest.eia_retail_sales` to `eia.retail_sales`. Update unique key examples.

5. **Common Commands section**: Update TABLE default in export example.

- [ ] **Step 2: Update README.md**

Update the Architecture mermaid diagram to show the eia schema. Update the Setup section if it references old schema names.

- [ ] **Step 3: Update docs/getting-started.md**

- Add `TRANSFORM_DATABASE_URL` to the environment setup section
- Update any SQL examples that reference `ingest.eia_*` to `eia.*`
- Update first-run backfill examples if they reference old table names

- [ ] **Step 4: Update docs/ingest-flows.md**

- Update directory references from `flows/eia_*.py` to `flows/ingest/eia/*.py`
- Update import examples to use new paths
- Update SQL examples from `ingest.eia_*` to `eia.*`
- Mention the dynamic backfill registry

- [ ] **Step 5: Update docs/data-analysis.md**

- Update all table references from `ingest.eia_*` to `eia.*`
- Update SQL query examples
- Update DBeaver connection instructions to mention both databases

- [ ] **Step 6: Update docs/README.md index**

Add entry for the design spec:
```markdown
- [Markdown-Driven Data Platform Design](superpowers/specs/2026-04-10-markdown-driven-data-platform-design.md) — Architecture spec for the layered data platform
```

- [ ] **Step 7: Commit**

```bash
git add CLAUDE.md README.md docs/
git commit -m "$(cat <<'EOF'
update all documentation for eia.* schema and new package structure

Updates CLAUDE.md, README.md, and all docs/ guides to reflect the
source-as-schema naming (eia.*), new client/db/flow package paths,
transform database, and quality schema.
EOF
)"
```

---

## Task 10: End-to-End Verification

Verify the full stack works with the new structure.

**Files:** None — verification only.

- [ ] **Step 1: Run unit tests**

```bash
uv run pytest tests/unit/ -v
```

Expected: All pass.

- [ ] **Step 2: Verify all Python imports resolve**

```bash
uv run python -c "
from energy_usa.config import Settings
from energy_usa.clients import EIAClient, EIAManager, DataClient
from energy_usa.db.connection import get_connection
from energy_usa.db.period import normalize_period
from energy_usa.db.dataframe import query_to_dataframe
from energy_usa.db.ingest.eia import upsert_retail_sales, upsert_co2_emissions
from energy_usa.flows.ingest.eia.retail_sales import ingest_eia_retail_sales
from energy_usa.flows.ingest.backfill import backfill_eia, get_flow_registry

registry = get_flow_registry('eia')
assert len(registry) == 36, f'Expected 36 flows, got {len(registry)}'

s = Settings()
assert hasattr(s, 'transform_database_url')

print(f'All imports OK. {len(registry)} EIA flows discovered.')
"
```

Expected: `All imports OK. 36 EIA flows discovered.`

- [ ] **Step 3: Fresh Docker stack test (if Docker available)**

```bash
# Destroy existing volumes to test fresh init
docker compose down -v
docker compose up -d postgres
# Wait for postgres to be ready
sleep 5
# Check that eia schema exists with tables
docker compose exec postgres psql -U energy -d ingest -c "\dt eia.*"
# Check quality schema
docker compose exec postgres psql -U energy -d ingest -c "\dt quality.*"
# Check transform database exists
docker compose exec postgres psql -U energy -d transform -c "SELECT 1"
docker compose down
```

Expected: `eia.*` tables listed, `quality.*` tables listed, transform database connectable.

- [ ] **Step 4: Commit any fixes discovered during verification**

If any issues are found, fix them and commit with a descriptive message.
