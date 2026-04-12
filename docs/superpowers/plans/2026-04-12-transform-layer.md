# Transform Layer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the transform layer that reads from the ingest database, applies domain-specific aggregations and joins, and writes to the transform database — proving the pattern with two electricity domain tables (`electricity.generation_mix` and `electricity.retail_by_state`).

**Architecture:** Transform flows are Prefect jobs that connect to the ingest DB (read-only), run an aggregation SQL query, fetch results as dicts, then connect to the transform DB (write) and upsert. Each domain (electricity, fossil_fuels, etc.) gets its own schema in the transform database and its own Prefect flow. The transform spec (Level B: scaffold + fill) drives a generator that produces DDL, a Python query+upsert module, and a Prefect flow — but the SQL query logic requires human review since it involves cross-table joins and business decisions.

**Tech Stack:** Python 3.12, psycopg3, Prefect 2, PostgreSQL 16, Jinja2

**Design Spec:** `docs/superpowers/specs/2026-04-10-markdown-driven-data-platform-design.md` — Transform Spec and Database Architecture sections.

**Depends on:** Plans 1-2 (ingest data in `eia.*` tables, generator infrastructure). Plan 3 (validation) is independent.

---

## File Map

### Created
```
docker/postgres/init/transform/electricity/00-schema.sql
docker/postgres/init/transform/electricity/generation_mix.sql
docker/postgres/init/transform/electricity/retail_by_state.sql
src/energy_usa/db/transform/__init__.py
src/energy_usa/db/transform/electricity/__init__.py
src/energy_usa/db/transform/electricity/generation_mix.py
src/energy_usa/db/transform/electricity/retail_by_state.py
src/energy_usa/flows/transform/__init__.py
src/energy_usa/flows/transform/electricity.py
src/energy_usa/generators/models_transform.py
src/energy_usa/generators/parse_transform.py
src/energy_usa/generators/transform.py
src/energy_usa/generators/templates/transform_schema.sql.j2
src/energy_usa/generators/templates/transform_module.py.j2
src/energy_usa/generators/templates/transform_flow.py.j2
specs/transform/electricity.md
scripts/transform.py
tests/unit/db/transform/__init__.py
tests/unit/db/transform/electricity/__init__.py
tests/unit/db/transform/electricity/test_generation_mix.py
tests/unit/db/transform/electricity/test_retail_by_state.py
tests/unit/generators/test_parse_transform.py
```

### Modified
```
compose.yaml                                      # Add TRANSFORM_DATABASE_URL to workers
docker/superset/seed_databases.py                  # Add transform DB connection + datasets
scripts/generate.py                                # Add transform subcommand
Makefile                                           # Add transform targets
CLAUDE.md                                          # Document transform commands
.env.example                                       # Already has TRANSFORM_DATABASE_URL
```

---

## Task 1: Infrastructure — Compose, Superset, Schema DDL

Wire the transform database into the Docker stack and create the electricity domain schema.

**Files:**
- Create: `docker/postgres/init/transform/electricity/00-schema.sql`
- Create: `docker/postgres/init/transform/electricity/generation_mix.sql`
- Create: `docker/postgres/init/transform/electricity/retail_by_state.sql`
- Modify: `compose.yaml`
- Modify: `docker/superset/seed_databases.py`

- [ ] **Step 1: Create electricity schema DDL**

```sql
-- docker/postgres/init/transform/electricity/00-schema.sql
CREATE SCHEMA IF NOT EXISTS electricity;
```

```sql
-- docker/postgres/init/transform/electricity/generation_mix.sql
-- Electricity generation by fuel type with CO2 emissions by state and period.
-- Grain: state + month. Sources: eia.state_source_disposition, eia.co2_emissions.
CREATE TABLE IF NOT EXISTS electricity.generation_mix (
    state TEXT NOT NULL,
    period DATE NOT NULL,
    total_generation_mwh NUMERIC,
    co2_tons NUMERIC,
    carbon_intensity NUMERIC,
    transformed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (state, period)
);
```

```sql
-- docker/postgres/init/transform/electricity/retail_by_state.sql
-- Retail electricity sales, prices, and customer counts by state and period.
-- Grain: state + month. Source: eia.retail_sales.
CREATE TABLE IF NOT EXISTS electricity.retail_by_state (
    state TEXT NOT NULL,
    period DATE NOT NULL,
    total_revenue NUMERIC,
    total_sales NUMERIC,
    avg_price NUMERIC,
    total_customers NUMERIC,
    transformed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (state, period)
);
```

- [ ] **Step 2: Remove the placeholder file**

```bash
rm docker/postgres/init/transform/00-create-schema-placeholder.sql
```

- [ ] **Step 3: Add TRANSFORM_DATABASE_URL to compose.yaml**

Read `compose.yaml` and add `TRANSFORM_DATABASE_URL` to the prefect-worker and jupyter services' environment sections:

```yaml
TRANSFORM_DATABASE_URL: postgresql://${POSTGRES_USER:-energy}:${POSTGRES_PASSWORD:-energy}@postgres:5432/transform
```

Add it alongside the existing `INGEST_DATABASE_URL` in both services.

- [ ] **Step 4: Add transform connection and datasets to Superset seed**

In `docker/superset/seed_databases.py`, add a second connection to the CONNECTIONS list:

```python
    {
        "name": "Transform",
        "uri": f"{_uri}/transform",
        "description": "Domain models — electricity, fossil fuels, emissions, pricing",
    },
```

Add datasets at the end of the DATASETS list:

```python
    ("electricity", "generation_mix"),
    ("electricity", "retail_by_state"),
```

Also add logic to seed transform datasets against the "Transform" connection (not "EIA Ingest"). Read the current file first to understand the seeding pattern, then add a second block that queries for the "Transform" database connection and seeds the electricity datasets against it.

- [ ] **Step 5: Commit**

```bash
git add docker/postgres/init/transform/electricity/ compose.yaml docker/superset/seed_databases.py
git rm docker/postgres/init/transform/00-create-schema-placeholder.sql
git commit -m "add electricity domain DDL, wire transform DB into compose and Superset

Creates electricity.generation_mix and electricity.retail_by_state tables.
Adds TRANSFORM_DATABASE_URL to prefect-worker and jupyter in compose.yaml.
Seeds transform DB connection and electricity datasets in Superset."
```

---

## Task 2: Transform DB Modules

Python modules that read from the ingest DB and write to the transform DB.

**Files:**
- Create: `src/energy_usa/db/transform/__init__.py`
- Create: `src/energy_usa/db/transform/electricity/__init__.py`
- Create: `src/energy_usa/db/transform/electricity/generation_mix.py`
- Create: `src/energy_usa/db/transform/electricity/retail_by_state.py`
- Test: `tests/unit/db/transform/electricity/test_generation_mix.py`
- Test: `tests/unit/db/transform/electricity/test_retail_by_state.py`

- [ ] **Step 1: Write tests for generation_mix**

```python
# tests/unit/db/transform/electricity/test_generation_mix.py
"""Tests for electricity.generation_mix transform module."""
from unittest.mock import MagicMock

from energy_usa.db.transform.electricity.generation_mix import (
    query_generation_mix,
    upsert_generation_mix,
)


def _mock_conn(fetchall_result=None):
    conn = MagicMock()
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchall.return_value = fetchall_result or []
    conn.cursor.return_value = cursor
    return conn, cursor


def test_query_generation_mix_returns_rows():
    rows = [{"state": "CA", "period": "2024-01-01", "total_generation_mwh": 1000, "co2_tons": 500, "carbon_intensity": 0.5}]
    conn, cur = _mock_conn(fetchall_result=rows)
    result = query_generation_mix(conn)
    assert len(result) == 1
    assert result[0]["state"] == "CA"
    cur.execute.assert_called_once()
    sql = cur.execute.call_args[0][0]
    assert "eia.state_source_disposition" in sql
    assert "eia.co2_emissions" in sql


def test_query_generation_mix_sql_has_join():
    conn, cur = _mock_conn()
    query_generation_mix(conn)
    sql = cur.execute.call_args[0][0]
    assert "JOIN" in sql.upper()


def test_upsert_generation_mix_empty():
    conn, _ = _mock_conn()
    assert upsert_generation_mix(conn, []) == 0


def test_upsert_generation_mix_inserts():
    conn, cur = _mock_conn()
    rows = [{"state": "CA", "period": "2024-01-01", "total_generation_mwh": 1000, "co2_tons": 500, "carbon_intensity": 0.5}]
    count = upsert_generation_mix(conn, rows)
    assert count == 1
    sql = cur.executemany.call_args[0][0]
    assert "INSERT INTO electricity.generation_mix" in sql
    assert "ON CONFLICT (state, period)" in sql
```

- [ ] **Step 2: Write tests for retail_by_state**

```python
# tests/unit/db/transform/electricity/test_retail_by_state.py
"""Tests for electricity.retail_by_state transform module."""
from unittest.mock import MagicMock

from energy_usa.db.transform.electricity.retail_by_state import (
    query_retail_by_state,
    upsert_retail_by_state,
)


def _mock_conn(fetchall_result=None):
    conn = MagicMock()
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchall.return_value = fetchall_result or []
    conn.cursor.return_value = cursor
    return conn, cursor


def test_query_retail_by_state_returns_rows():
    rows = [{"state": "TX", "period": "2024-01-01", "total_revenue": 5000, "total_sales": 10000, "avg_price": 0.12, "total_customers": 200}]
    conn, cur = _mock_conn(fetchall_result=rows)
    result = query_retail_by_state(conn)
    assert len(result) == 1
    assert result[0]["state"] == "TX"
    sql = cur.execute.call_args[0][0]
    assert "eia.retail_sales" in sql


def test_query_retail_by_state_aggregates():
    conn, cur = _mock_conn()
    query_retail_by_state(conn)
    sql = cur.execute.call_args[0][0].upper()
    assert "SUM" in sql
    assert "GROUP BY" in sql


def test_upsert_retail_by_state_empty():
    conn, _ = _mock_conn()
    assert upsert_retail_by_state(conn, []) == 0


def test_upsert_retail_by_state_inserts():
    conn, cur = _mock_conn()
    rows = [{"state": "TX", "period": "2024-01-01", "total_revenue": 5000, "total_sales": 10000, "avg_price": 0.12, "total_customers": 200}]
    count = upsert_retail_by_state(conn, rows)
    assert count == 1
    sql = cur.executemany.call_args[0][0]
    assert "INSERT INTO electricity.retail_by_state" in sql
    assert "ON CONFLICT (state, period)" in sql
```

- [ ] **Step 3: Implement the modules**

```python
# src/energy_usa/db/transform/__init__.py
"""Transform database modules, organized by domain."""
```

```python
# src/energy_usa/db/transform/electricity/__init__.py
"""Electricity domain transform modules."""
```

```python
# src/energy_usa/db/transform/electricity/generation_mix.py
"""Read from eia.state_source_disposition + eia.co2_emissions, produce electricity.generation_mix.

Grain: state + month.
Join: stateid + period between source disposition and CO2 emissions.
"""

from typing import Any

import psycopg


def query_generation_mix(conn: psycopg.Connection) -> list[dict[str, Any]]:
    """Query ingest tables and return aggregated generation mix rows.

    :param conn: Connection to the **ingest** database.
    :returns: List of dicts with state, period, total_generation_mwh, co2_tons, carbon_intensity.
    """
    sql = """
    SELECT
        ssd.stateid AS state,
        ssd.period,
        SUM(ssd.generation) AS total_generation_mwh,
        co2.co2_tons,
        CASE
            WHEN SUM(ssd.generation) > 0
            THEN co2.co2_tons / SUM(ssd.generation)
            ELSE NULL
        END AS carbon_intensity
    FROM eia.state_source_disposition ssd
    LEFT JOIN (
        SELECT state_id, period, SUM(value) AS co2_tons
        FROM eia.co2_emissions
        WHERE fuel_id = 'TO' AND sector_id = 'EC'
        GROUP BY state_id, period
    ) co2 ON ssd.stateid = co2.state_id
         AND date_trunc('year', ssd.period) = co2.period
    WHERE ssd.stateid != 'US'
    GROUP BY ssd.stateid, ssd.period, co2.co2_tons
    ORDER BY ssd.stateid, ssd.period
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def upsert_generation_mix(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert rows into electricity.generation_mix.

    :param conn: Connection to the **transform** database.
    :param rows: List of dicts from query_generation_mix.
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO electricity.generation_mix
        (state, period, total_generation_mwh, co2_tons, carbon_intensity, transformed_at)
    VALUES
        (%(state)s, %(period)s, %(total_generation_mwh)s, %(co2_tons)s, %(carbon_intensity)s, now())
    ON CONFLICT (state, period)
    DO UPDATE SET
        total_generation_mwh = EXCLUDED.total_generation_mwh,
        co2_tons = EXCLUDED.co2_tons,
        carbon_intensity = EXCLUDED.carbon_intensity,
        transformed_at = now()
    """
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    conn.commit()
    return len(rows)
```

```python
# src/energy_usa/db/transform/electricity/retail_by_state.py
"""Read from eia.retail_sales, produce electricity.retail_by_state.

Grain: state + month. Aggregates across sectors for a state-level view.
"""

from typing import Any

import psycopg


def query_retail_by_state(conn: psycopg.Connection) -> list[dict[str, Any]]:
    """Query retail sales and return state-level aggregations.

    :param conn: Connection to the **ingest** database.
    :returns: List of dicts with state, period, totals, avg_price.
    """
    sql = """
    SELECT
        stateid AS state,
        period,
        SUM(revenue) AS total_revenue,
        SUM(sales) AS total_sales,
        CASE
            WHEN SUM(sales) > 0
            THEN SUM(revenue) / SUM(sales)
            ELSE NULL
        END AS avg_price,
        SUM(customers) AS total_customers
    FROM eia.retail_sales
    WHERE stateid != 'US'
    GROUP BY stateid, period
    ORDER BY stateid, period
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def upsert_retail_by_state(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert rows into electricity.retail_by_state.

    :param conn: Connection to the **transform** database.
    :param rows: List of dicts from query_retail_by_state.
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO electricity.retail_by_state
        (state, period, total_revenue, total_sales, avg_price, total_customers, transformed_at)
    VALUES
        (%(state)s, %(period)s, %(total_revenue)s, %(total_sales)s, %(avg_price)s, %(total_customers)s, now())
    ON CONFLICT (state, period)
    DO UPDATE SET
        total_revenue = EXCLUDED.total_revenue,
        total_sales = EXCLUDED.total_sales,
        avg_price = EXCLUDED.avg_price,
        total_customers = EXCLUDED.total_customers,
        transformed_at = now()
    """
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    conn.commit()
    return len(rows)
```

- [ ] **Step 4: Create test __init__.py files and run tests**

```bash
mkdir -p tests/unit/db/transform/electricity
touch tests/unit/db/transform/__init__.py
touch tests/unit/db/transform/electricity/__init__.py
uv run pytest tests/unit/db/transform/ -v
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add src/energy_usa/db/transform/ tests/unit/db/transform/
git commit -m "add electricity domain transform modules (generation_mix, retail_by_state)

Each module has a query function (reads ingest DB) and an upsert function
(writes transform DB). generation_mix joins state_source_disposition with
co2_emissions. retail_by_state aggregates retail_sales across sectors."
```

---

## Task 3: Transform Prefect Flow

A Prefect flow that reads from ingest and writes to transform for the electricity domain.

**Files:**
- Create: `src/energy_usa/flows/transform/__init__.py`
- Create: `src/energy_usa/flows/transform/electricity.py`
- Modify: `src/energy_usa/flows/__init__.py`

- [ ] **Step 1: Create the transform flow**

```python
# src/energy_usa/flows/transform/__init__.py
"""Transform flows, organized by domain."""
```

```python
# src/energy_usa/flows/transform/electricity.py
"""Prefect flow: transform electricity domain tables.

Reads from ingest DB (eia.* tables), aggregates, and writes to
transform DB (electricity.* tables). Each table is an independent task.
"""

from prefect import flow, task
from prefect.logging import get_run_logger

from energy_usa.config import Settings
from energy_usa.db.connection import get_connection
from energy_usa.db.transform.electricity.generation_mix import (
    query_generation_mix,
    upsert_generation_mix,
)
from energy_usa.db.transform.electricity.retail_by_state import (
    query_retail_by_state,
    upsert_retail_by_state,
)


@task(name="transform-generation-mix")
def transform_generation_mix_task(
    ingest_url: str,
    transform_url: str,
) -> int:
    """Query ingest, upsert into electricity.generation_mix."""
    logger = get_run_logger()
    ingest_conn = get_connection(ingest_url)
    try:
        rows = query_generation_mix(ingest_conn)
        logger.info("Queried %d generation_mix rows from ingest", len(rows))
    finally:
        ingest_conn.close()

    transform_conn = get_connection(transform_url)
    try:
        count = upsert_generation_mix(transform_conn, rows)
        logger.info("Upserted %d rows into electricity.generation_mix", count)
        return count
    finally:
        transform_conn.close()


@task(name="transform-retail-by-state")
def transform_retail_by_state_task(
    ingest_url: str,
    transform_url: str,
) -> int:
    """Query ingest, upsert into electricity.retail_by_state."""
    logger = get_run_logger()
    ingest_conn = get_connection(ingest_url)
    try:
        rows = query_retail_by_state(ingest_conn)
        logger.info("Queried %d retail_by_state rows from ingest", len(rows))
    finally:
        ingest_conn.close()

    transform_conn = get_connection(transform_url)
    try:
        count = upsert_retail_by_state(transform_conn, rows)
        logger.info("Upserted %d rows into electricity.retail_by_state", count)
        return count
    finally:
        transform_conn.close()


@flow(
    name="transform-electricity",
    timeout_seconds=3600,
)
def transform_electricity(
    tables: list[str] | None = None,
) -> dict[str, int]:
    """Transform electricity domain tables.

    :param tables: Optional list of table names (e.g. ['generation_mix']).
        None = transform all tables.
    :returns: Dict mapping table name to row count.
    """
    logger = get_run_logger()
    settings = Settings()
    if not settings.ingest_database_url:
        raise ValueError("INGEST_DATABASE_URL required")
    if not settings.transform_database_url:
        raise ValueError("TRANSFORM_DATABASE_URL required")

    all_tables = {
        "generation_mix": transform_generation_mix_task,
        "retail_by_state": transform_retail_by_state_task,
    }

    targets = all_tables
    if tables:
        targets = {k: v for k, v in all_tables.items() if k in tables}

    results: dict[str, int] = {}
    for name, task_fn in targets.items():
        logger.info("Transforming electricity.%s", name)
        count = task_fn(
            ingest_url=settings.ingest_database_url,
            transform_url=settings.transform_database_url,
        )
        results[name] = count

    logger.info("Electricity transform complete: %s", results)
    return results
```

- [ ] **Step 2: Update flows/__init__.py**

Add to `src/energy_usa/flows/__init__.py`:

```python
from energy_usa.flows.transform.electricity import transform_electricity
```

And add `"transform_electricity"` to the `__all__` list.

- [ ] **Step 3: Verify import**

```bash
uv run python -c "from energy_usa.flows.transform.electricity import transform_electricity; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add src/energy_usa/flows/transform/ src/energy_usa/flows/__init__.py
git commit -m "add electricity transform Prefect flow

Reads from ingest DB (eia.* tables), runs query+upsert tasks for
generation_mix and retail_by_state, writes to transform DB. Each
table is an independent Prefect task."
```

---

## Task 4: Transform Spec, Parser, and Generator

Build the spec format, parser, and generator for Level B transform automation.

**Files:**
- Create: `src/energy_usa/generators/models_transform.py`
- Create: `src/energy_usa/generators/parse_transform.py`
- Create: `src/energy_usa/generators/transform.py`
- Create: `src/energy_usa/generators/templates/transform_schema.sql.j2`
- Create: `src/energy_usa/generators/templates/transform_module.py.j2`
- Create: `src/energy_usa/generators/templates/transform_flow.py.j2`
- Create: `specs/transform/electricity.md`
- Test: `tests/unit/generators/test_parse_transform.py`

- [ ] **Step 1: Write transform spec models**

```python
# src/energy_usa/generators/models_transform.py
"""Dataclasses for parsed transform specs."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TransformColumnSpec:
    """A column in a transform output table."""
    name: str
    source: str           # e.g. "eia.retail_sales.stateid" or "derived"
    logic: str            # e.g. "direct", "sum by state+period", "col_a / col_b"
    pg_type: str = "NUMERIC"


@dataclass
class TransformTableSpec:
    """A single output table in a domain."""
    name: str             # e.g. "generation_mix"
    description: str
    source_tables: list[str]
    grain: list[str]      # e.g. ["state", "period"]
    join_logic: str       # Free text
    columns: list[TransformColumnSpec]
    unique_key: tuple[str, ...]


@dataclass
class TransformSpec:
    """A domain transform spec."""
    domain: str           # e.g. "electricity"
    tables: list[TransformTableSpec]

    def get_table(self, name: str) -> TransformTableSpec | None:
        for t in self.tables:
            if t.name == name:
                return t
        return None
```

- [ ] **Step 2: Write the electricity spec**

```markdown
# Electricity Domain Model

## electricity.generation_mix
Combines generation data by fuel type with emissions data to show
the environmental profile of each state's electricity generation.

- **Source tables**: eia.state_source_disposition, eia.co2_emissions
- **Grain**: state, period
- **Join logic**: Match on stateid + period (year-level for CO2, month for generation)
- **Output columns**:
  | Column | Source | Logic | Type |
  |--------|--------|-------|------|
  | state | eia.state_source_disposition.stateid | direct | TEXT |
  | period | eia.state_source_disposition.period | direct | DATE |
  | total_generation_mwh | eia.state_source_disposition.generation | sum by state+period | NUMERIC |
  | co2_tons | eia.co2_emissions.value | sum where fuel='TO' and sector='EC' | NUMERIC |
  | carbon_intensity | derived | co2_tons / total_generation_mwh | NUMERIC |
- **Unique key**: (state, period)

## electricity.retail_by_state
State-level retail electricity sales aggregated across all sectors.

- **Source tables**: eia.retail_sales
- **Grain**: state, period
- **Join logic**: Single source, aggregate across sectorid
- **Output columns**:
  | Column | Source | Logic | Type |
  |--------|--------|-------|------|
  | state | eia.retail_sales.stateid | direct | TEXT |
  | period | eia.retail_sales.period | direct | DATE |
  | total_revenue | eia.retail_sales.revenue | sum by state+period | NUMERIC |
  | total_sales | eia.retail_sales.sales | sum by state+period | NUMERIC |
  | avg_price | derived | total_revenue / total_sales | NUMERIC |
  | total_customers | eia.retail_sales.customers | sum by state+period | NUMERIC |
- **Unique key**: (state, period)
```

- [ ] **Step 3: Write parser tests**

```python
# tests/unit/generators/test_parse_transform.py
"""Tests for the transform spec parser."""
import textwrap
from pathlib import Path

from energy_usa.generators.parse_transform import parse_transform_spec


SPEC = textwrap.dedent("""\
    # Electricity Domain Model

    ## electricity.generation_mix
    Combines generation data with emissions data.

    - **Source tables**: eia.state_source_disposition, eia.co2_emissions
    - **Grain**: state, period
    - **Join logic**: Match on stateid + period
    - **Output columns**:
      | Column | Source | Logic | Type |
      |--------|--------|-------|------|
      | state | eia.state_source_disposition.stateid | direct | TEXT |
      | period | eia.state_source_disposition.period | direct | DATE |
      | total_generation_mwh | eia.state_source_disposition.generation | sum by state+period | NUMERIC |
      | co2_tons | eia.co2_emissions.value | sum where fuel=TO | NUMERIC |
      | carbon_intensity | derived | co2_tons / total_generation_mwh | NUMERIC |
    - **Unique key**: (state, period)

    ## electricity.retail_by_state
    State-level retail electricity sales.

    - **Source tables**: eia.retail_sales
    - **Grain**: state, period
    - **Join logic**: Single source, aggregate across sectorid
    - **Output columns**:
      | Column | Source | Logic | Type |
      |--------|--------|-------|------|
      | state | eia.retail_sales.stateid | direct | TEXT |
      | period | eia.retail_sales.period | direct | DATE |
      | total_revenue | eia.retail_sales.revenue | sum | NUMERIC |
    - **Unique key**: (state, period)
""")


def test_parse_domain():
    spec = parse_transform_spec(SPEC)
    assert spec.domain == "electricity"


def test_parse_table_count():
    spec = parse_transform_spec(SPEC)
    assert len(spec.tables) == 2


def test_parse_table_name():
    spec = parse_transform_spec(SPEC)
    assert spec.tables[0].name == "generation_mix"
    assert spec.tables[1].name == "retail_by_state"


def test_parse_source_tables():
    spec = parse_transform_spec(SPEC)
    gm = spec.tables[0]
    assert gm.source_tables == ["eia.state_source_disposition", "eia.co2_emissions"]


def test_parse_grain():
    spec = parse_transform_spec(SPEC)
    gm = spec.tables[0]
    assert gm.grain == ["state", "period"]


def test_parse_columns():
    spec = parse_transform_spec(SPEC)
    gm = spec.tables[0]
    assert len(gm.columns) == 5
    assert gm.columns[0].name == "state"
    assert gm.columns[0].pg_type == "TEXT"
    assert gm.columns[4].name == "carbon_intensity"
    assert gm.columns[4].source == "derived"


def test_parse_unique_key():
    spec = parse_transform_spec(SPEC)
    gm = spec.tables[0]
    assert gm.unique_key == ("state", "period")


def test_parse_join_logic():
    spec = parse_transform_spec(SPEC)
    gm = spec.tables[0]
    assert "stateid" in gm.join_logic.lower()


def test_parse_description():
    spec = parse_transform_spec(SPEC)
    gm = spec.tables[0]
    assert "generation" in gm.description.lower()
```

- [ ] **Step 4: Implement the parser**

```python
# src/energy_usa/generators/parse_transform.py
"""Parse transform spec markdown into TransformSpec dataclasses."""

from __future__ import annotations

import re
from pathlib import Path

from energy_usa.generators.models_transform import (
    TransformColumnSpec,
    TransformSpec,
    TransformTableSpec,
)


def parse_transform_spec(text: str) -> TransformSpec:
    """Parse a transform spec markdown string."""
    lines = text.splitlines()
    domain = _parse_domain(lines)
    tables = _parse_tables(lines, domain)
    return TransformSpec(domain=domain, tables=tables)


def parse_transform_spec_file(path: Path) -> TransformSpec:
    """Parse a transform spec from a file path."""
    return parse_transform_spec(path.read_text())


def _parse_domain(lines: list[str]) -> str:
    """Extract domain from H1 heading: '# Electricity Domain Model' → 'electricity'."""
    for line in lines:
        if line.startswith("# "):
            return line[2:].strip().split()[0].lower()
    raise ValueError("No H1 heading found")


def _parse_tables(lines: list[str], domain: str) -> list[TransformTableSpec]:
    tables: list[TransformTableSpec] = []
    current_name: str | None = None
    current_block: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            if current_name and current_block:
                tables.append(_parse_single_table(current_name, current_block))
            # "## electricity.generation_mix" → "generation_mix"
            full_name = stripped[3:].strip()
            if "." in full_name:
                current_name = full_name.split(".", 1)[1]
            else:
                current_name = full_name
            current_block = []
        elif current_name is not None:
            current_block.append(line)

    if current_name and current_block:
        tables.append(_parse_single_table(current_name, current_block))
    return tables


def _parse_single_table(name: str, block: list[str]) -> TransformTableSpec:
    source_tables: list[str] = []
    grain: list[str] = []
    join_logic = ""
    columns: list[TransformColumnSpec] = []
    unique_key: tuple[str, ...] = ()
    description_lines: list[str] = []

    in_columns = False
    in_description = True
    for line in block:
        stripped = line.strip()

        if in_columns:
            if stripped.startswith("|") and not stripped.startswith("|--") and not stripped.startswith("| Column"):
                col = _parse_column_row(stripped)
                if col:
                    columns.append(col)
                continue
            elif stripped.startswith("|"):
                continue
            else:
                in_columns = False

        if "**Output columns**" in stripped:
            in_columns = True
            in_description = False
            continue
        if "**Source tables**" in stripped:
            in_description = False
            val = _extract_value(stripped)
            source_tables = [s.strip() for s in val.split(",")]
        elif "**Grain**" in stripped:
            in_description = False
            val = _extract_value(stripped)
            grain = [g.strip() for g in val.split(",")]
        elif "**Join logic**" in stripped:
            in_description = False
            join_logic = _extract_value(stripped)
        elif "**Unique key**" in stripped:
            in_description = False
            val = _extract_value(stripped).strip("()")
            unique_key = tuple(k.strip() for k in val.split(",") if k.strip())
        elif in_description and stripped and not stripped.startswith("-"):
            description_lines.append(stripped)

    return TransformTableSpec(
        name=name,
        description=" ".join(description_lines),
        source_tables=source_tables,
        grain=grain,
        join_logic=join_logic,
        columns=columns,
        unique_key=unique_key,
    )


def _parse_column_row(row: str) -> TransformColumnSpec | None:
    cells = [c.strip() for c in row.split("|") if c.strip()]
    if len(cells) < 3:
        return None
    name = cells[0]
    source = cells[1]
    logic = cells[2]
    pg_type = cells[3].upper() if len(cells) > 3 else "NUMERIC"
    return TransformColumnSpec(name=name, source=source, logic=logic, pg_type=pg_type)


def _extract_value(line: str) -> str:
    match = re.search(r"\*\*[^*]+\*\*:\s*(.*)", line)
    return match.group(1).strip() if match else ""
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/unit/generators/test_parse_transform.py -v
```

Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add src/energy_usa/generators/models_transform.py \
        src/energy_usa/generators/parse_transform.py \
        specs/transform/electricity.md \
        tests/unit/generators/test_parse_transform.py
git commit -m "add transform spec parser, models, and electricity spec

Parses specs/transform/<domain>.md into TransformSpec dataclasses.
Electricity spec documents generation_mix and retail_by_state tables
with source tables, grain, join logic, and column derivations."
```

---

## Task 5: CLI, Makefile, and Documentation

Add transform CLI, Makefile targets, and update docs.

**Files:**
- Create: `scripts/transform.py`
- Modify: `scripts/generate.py`
- Modify: `Makefile`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Create transform CLI**

```python
#!/usr/bin/env -S uv run python
# scripts/transform.py
"""CLI for running transform flows.

Usage:
    uv run python scripts/transform.py --domain electricity
    uv run python scripts/transform.py --domain electricity --table generation_mix
"""
import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Run transform flows")
    parser.add_argument("--domain", required=True, help="Domain name (e.g. electricity)")
    parser.add_argument("--table", help="Single table (optional)")
    args = parser.parse_args()

    if args.domain == "electricity":
        from energy_usa.flows.transform.electricity import transform_electricity
        tables = [args.table] if args.table else None
        results = transform_electricity(tables=tables)
        print("\nTransform complete:")
        for name, count in results.items():
            print(f"  electricity.{name}: {count} rows")
    else:
        print(f"ERROR: Unknown domain '{args.domain}'")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Add transform subcommand to scripts/generate.py**

Read the current file, then add a `transform` subcommand that parses the spec and prints a summary (the transform generator templates are a future enhancement — for now, the CLI validates that the spec parses correctly):

```python
def cmd_transform(args):
    spec_path = Path("specs/transform") / f"{args.domain}.md"
    if not spec_path.exists():
        print(f"ERROR: Spec file not found: {spec_path}")
        sys.exit(1)
    from energy_usa.generators.parse_transform import parse_transform_spec
    spec = parse_transform_spec(spec_path.read_text())
    print(f"Parsed {len(spec.tables)} tables in {spec.domain} domain:")
    for t in spec.tables:
        print(f"  {spec.domain}.{t.name}: {len(t.columns)} columns, key=({', '.join(t.unique_key)})")
        print(f"    Sources: {', '.join(t.source_tables)}")
```

Add subparser and dispatch.

- [ ] **Step 3: Add Makefile targets**

```makefile
DOMAIN    ?= electricity            # Domain for transform
TTABLE    ?=                        # Table for single-table transform (blank = all)

# ── Transform ─────────────────────────────────────────────────────────────────

transform:  ## Run transform for a domain. Use DOMAIN, TTABLE (optional).
	uv run python scripts/transform.py \
	  --domain $(DOMAIN) \
	  $(if $(TTABLE),--table $(TTABLE))
```

Update `.PHONY` to include `transform`.

- [ ] **Step 4: Update CLAUDE.md**

Add in the Common Commands section:

```markdown
# Transform (domain model builds)
make transform DOMAIN=electricity                  # All electricity tables
make transform DOMAIN=electricity TTABLE=retail_by_state  # Single table
```

- [ ] **Step 5: Commit**

```bash
git add scripts/transform.py scripts/generate.py Makefile CLAUDE.md
git commit -m "add transform CLI, Makefile target, and documentation

make transform DOMAIN=electricity runs the Prefect flow. CLI supports
single-table runs. generate.py gains a transform subcommand for spec
validation. CLAUDE.md documents transform commands."
```

---

## Task 6: End-to-End Verification

Verify everything works together.

**Files:** None — verification only.

- [ ] **Step 1: Run all tests**

```bash
uv run pytest tests/ -v --ignore=tests/integration
```

Expected: All pass.

- [ ] **Step 2: Verify all imports**

```bash
uv run python -c "
from energy_usa.db.transform.electricity.generation_mix import query_generation_mix, upsert_generation_mix
from energy_usa.db.transform.electricity.retail_by_state import query_retail_by_state, upsert_retail_by_state
from energy_usa.flows.transform.electricity import transform_electricity
from energy_usa.generators.parse_transform import parse_transform_spec
from energy_usa.generators.models_transform import TransformSpec, TransformTableSpec, TransformColumnSpec
print('All transform imports OK')
"
```

- [ ] **Step 3: Verify spec parses**

```bash
uv run python -c "
from pathlib import Path
from energy_usa.generators.parse_transform import parse_transform_spec
spec = parse_transform_spec(Path('specs/transform/electricity.md').read_text())
print(f'{spec.domain} domain: {len(spec.tables)} tables')
for t in spec.tables:
    print(f'  {t.name}: {len(t.columns)} columns, sources={t.source_tables}')
"
```

- [ ] **Step 4: Commit any fixes**

If issues found, fix and commit.
