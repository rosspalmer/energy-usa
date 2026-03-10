---
name: jupyter-postgres
description: Standard workflow for Jupyter notebooks and Postgres in this repo. Use when adding or using the Jupyter service in Docker Compose, running notebooks, querying Postgres from notebooks, or extracting DB data into Pandas DataFrames.
---

# Jupyter + Postgres

## When to use this skill

Apply this skill when:

- Adding, configuring, or documenting the Jupyter notebook service in Docker Compose
- User asks about Jupyter, notebooks, or running analysis in a notebook
- Notebooks need to query Postgres or load data into Pandas DataFrames
- User mentions extracting data from Postgres into pandas, or SQL in notebooks

## Standard notebook environment

- **Service:** `jupyter` in `compose.yaml`; UI at **http://localhost:8888**
- **Dependencies:** Jupyter image installs project deps including base + `web` + notebook extras (see `pyproject.toml` and `Dockerfile.jupyter`)
- **Databases:**
  - `DATABASE_URL` — main app DB (e.g. `energy_usa`). Use for display/dashboard tables.
  - `INGEST_DATABASE_URL` — ingest DB (e.g. `ingest`). Use for EIA ingest tables (`eia_retail_sales`, `eia_electric_power_operational`, etc.).
- **Notebook workspace:** Typically mounted at `/app/notebooks` (or `./notebooks` on host). Create notebooks there so they persist and have access to project code.

## Postgres → Pandas workflow

1. **Prefer the project helper** when available: `energy_usa.db.query_to_dataframe(database_url, sql, params=None)` returns a `pandas.DataFrame`. Use it so connection handling and parameterization stay consistent.
2. **Fallback** if the helper is not yet implemented: open a connection with `energy_usa.db.get_connection(database_url)`, then use `pandas.read_sql_query(sql, conn, params=params)`. Close the connection when done (or use a context manager).
3. **Safety:** Always use parameterized queries (e.g. `%(name)s` with a `params` dict). Do not embed secrets in notebook code; read `DATABASE_URL` / `INGEST_DATABASE_URL` from the environment. During exploration, add `LIMIT n` to avoid large result sets.

## Examples

**Preferred: project helper (when implemented)**

```python
import os
from energy_usa.db import query_to_dataframe

url = os.environ["INGEST_DATABASE_URL"]
df = query_to_dataframe(url, "SELECT period, stateid, sectorid, sales FROM eia_retail_sales LIMIT 100")
df.head()
```

**Fallback: connection + read_sql_query**

```python
import os
import pandas as pd
from energy_usa.db import get_connection

url = os.environ["INGEST_DATABASE_URL"]
with get_connection(url) as conn:
    df = pd.read_sql_query(
        "SELECT period, stateid, sectorid, sales FROM eia_retail_sales WHERE stateid = %(state)s LIMIT 100",
        conn,
        params={"state": "NY"},
    )
df.head()
```

**Choosing the right database URL**

- Ingest tables (`eia_retail_sales`, `eia_electric_power_operational`, `eia_state_source_disposition`, `eia_state_summary`) → use `INGEST_DATABASE_URL`
- Display or dashboard tables (if present) → use `DATABASE_URL`

## Troubleshooting

- **Connection refused / could not connect:** Ensure Postgres and the Jupyter service are up (`docker compose ps`). From inside the Jupyter container, use hostname `postgres` and port `5432`; `DATABASE_URL` in compose should already point to `postgres:5432`.
- **Missing env var:** Jupyter service must receive `DATABASE_URL` and `INGEST_DATABASE_URL` in `compose.yaml` (same pattern as the `web` service). Restart the stack after changing env.
- **Wrong database:** Verify which DB has the table (ingest vs main). Use `INGEST_DATABASE_URL` for EIA ingest tables, `DATABASE_URL` for the main app DB.
- **Module not found (energy_usa):** Ensure the Jupyter image copies the project source and sets `PYTHONPATH` so `import energy_usa` resolves (e.g. `PYTHONPATH=/app` or `/app/src` depending on layout).

## This project

- DB connection helper: `src/energy_usa/db/retail_sales.py` defines `get_connection(database_url)`; use it for fallback SQL in notebooks.
- Postgres-to-DataFrame helper: when present, use `energy_usa.db.query_to_dataframe` from `src/energy_usa/db/dataframe.py` (and re-exported in `src/energy_usa/db/__init__.py`).
- Compose and scripts: `compose.yaml` for the `jupyter` service; `dock.sh` for starting the stack and optional Jupyter URL in usage output.
