# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

Energy USA serves two audiences simultaneously:
- **Data engineer** (primary): Production-grade infrastructure using real tools (Prefect, Postgres, Docker, Superset)
- **Industry professional learning tech** (secondary): Must be able to follow along, debug, and eventually build simple pipelines with AI assistance

All architectural decisions should keep both audiences in mind. Prefer explicit over clever. Documentation is a first-class deliverable — keep `docs/` up to date with every significant change.

## Package Manager

This project uses `uv`. Always use `uv run` to execute Python scripts.

```bash
uv sync                    # Install base dependencies
uv sync --extra notebook   # Include Jupyter + jupyter-ai dependencies
```

## Common Commands (Makefile)

`make` is the primary interface for day-to-day development. Install via `xcode-select --install` on macOS (usually already present).

```bash
make help                            # List all available targets

# Stack management
make up                              # Start full Docker Compose stack
make down                            # Stop stack
make logs SERVICE=prefect-worker     # Tail logs for a specific service

# Ingest — always run THROUGH Docker Prefect (requires stack up)
make deploy                          # Register deployments
make run FLOW=backfill-eia START=2020-01 END=2024-12

# Local development
make jupyter                         # Jupyter Lab (no Docker)

# Code generation (from markdown specs)
make generate-ingest SOURCE=eia                    # All EIA datasets
make generate-ingest SOURCE=eia GDATASET=retail_sales  # Single dataset

# Data export for analysis
make export TABLE=eia.retail_sales OUT=exports/retail_sales.csv
make export TABLE=eia.retail_sales FILTER="stateid='CA'" OUT=exports/ca_retail.csv
```

> **Note:** The Makefile wraps `dock.sh` for Docker targets. `dock.sh` remains available for lower-level Docker Compose control.

> **Important:** Always run ingest through Docker Prefect (`make run` or the Prefect API), never via `scripts/run_local.py`. The local runner uses Prefect's SQLite backend which hits concurrency/locking issues with backfills. The Docker stack uses Postgres for Prefect state, which handles concurrent child flows reliably.

## Local Development Without Docker

### Jupyter Lab
```bash
uv sync --extra notebook
make jupyter
```
Requires `INGEST_DATABASE_URL` in `.env` pointing to a running Postgres (Docker or local).

## Environment

Copy `.env.example` to `.env`. Required:
- `EIA_API_KEY` — register at [EIA Open Data](https://www.eia.gov/opendata/register.php)
- `INGEST_DATABASE_URL` — EIA raw data database

## Architecture

### Data Flow

```
EIA API → EIAClient → EIAManager → Prefect Flow → Postgres (eia.* schema)
                                                        ↓
                                              Validation Flows → quality.*
                                                        ↓
                                              Transform Flows → transform DB
                                                        ↓
                                                Superset Dashboard
```

### Key Components

**`src/energy_usa/`** — Core Python package, no Django dependency
- `clients/eia.py` — Async HTTP client with pagination, facet support, concurrency semaphore, and exponential backoff retries; implements the `DataClient` protocol from `clients/base.py`
- `db/connection.py` — Shared psycopg3 connection helper
- `db/ingest/eia/` — Direct psycopg3 SQL, no ORM; one module per table, all upserts are idempotent
- `db/dataframe.py` — `query_to_dataframe(url, sql)` for SQL → pandas
- `flows/ingest/eia/` — Prefect flows; each dataset = one fetch task + one upsert task; discovered dynamically at deploy time
- `flows/ingest/backfill.py` — Chunks date ranges and submits child flow runs via dynamic discovery
- `config.py` — pydantic-settings loaded from `.env`
- `generators/` — Development-time code generation from markdown specs
  - `models.py` — Dataclasses (SourceSpec, DatasetSpec, ColumnSpec)
  - `parse_spec.py` — Markdown parser for ingest specs
  - `ingest.py` — Generates SQL, db modules, and flow modules
  - `templates/` — Jinja2 templates for each output type
- `specs/ingest/eia.md` — Source of truth for all EIA dataset configurations

**`docker/postgres/init/`** — SQL run on first container start; source of truth for schemas
- `init/ingest/eia/` — Table DDL for all EIA datasets under the `eia` schema
- `init/ingest/00-quality-schema.sql` — Quality audit schema (`quality.*`)
- `init/transform/` — Transform database schema placeholder

### Databases

| Database | Connection var | Purpose |
|----------|---------------|---------|
| `ingest` | `INGEST_DATABASE_URL` | EIA raw data (`eia.*` schema), quality audits (`quality.*` schema) |
| `transform` | `TRANSFORM_DATABASE_URL` | Domain models (`electricity.*`, `fossil_fuels.*`, etc.) |

### Ingest Patterns

- All writes: idempotent upserts (`ON CONFLICT DO UPDATE`)
- Tables live in the `eia` schema: e.g. `eia.retail_sales`, `eia.electric_power_operational`
- Unique keys: `(period, stateid, sectorid)` or `(period, stateid)`
- Periods stored as `DATE`; annual data as `YYYY-01-01`
- Historical data is the priority — live/scheduled ingest is secondary

## Local Analytics with DuckDB

DuckDB runs in-process (no server, no Docker) and is the recommended tool for ad-hoc analysis and local testing of new queries before running against Postgres.

### In notebooks or scripts
```python
import duckdb

# In-memory for exploration
con = duckdb.connect()

# Persistent local file (survives sessions)
con = duckdb.connect("local_analysis.duckdb")

# Query a CSV export directly
con.execute("SELECT * FROM read_csv_auto('exports/retail_sales.csv') LIMIT 10").df()
```

### Connecting DBeaver to DuckDB

DBeaver Community (free) is the officially supported SQL GUI for this project.

1. Download [DBeaver Community](https://dbeaver.io/download/)
2. New Connection → search **DuckDB** → Next
3. **Path**: browse to your `.duckdb` file (e.g. `local_analysis.duckdb` in the project root), or enter `:memory:` for a throwaway session
4. Click **Test Connection** — DBeaver will auto-download the DuckDB JDBC driver on first connect
5. Finish

> For Postgres (Docker): New Connection → PostgreSQL → Host `localhost`, Port `5432`, Database `ingest`, User/Password from `.env`.

## AI-Assisted Analysis

### Option 1 — jupyter-ai (in Jupyter Lab)

The `jupyter` service includes `jupyter-ai` with Claude integration. Open any notebook and use the chat panel (✦ icon in the sidebar) or `%%ai` cell magic:

```python
%%ai anthropic:claude-sonnet-4-6
Summarize the trend in retail electricity sales for California from 2015 to 2023
using the dataframe `df` already loaded in this notebook.
```

Requires `ANTHROPIC_API_KEY` in `.env` (add to `.env.example`).

### Option 2 — Claude.ai with data exports (no setup required)

Best for quick, non-technical analysis. Export a slice of data to CSV and upload directly to claude.ai:

```bash
# Export a focused slice
make export TABLE=eia.retail_sales FILTER="stateid='TX' AND period > '2015-01-01'" OUT=exports/tx_retail.csv
```

Then at [claude.ai](https://claude.ai): attach the CSV and ask questions in plain English. No code required. Useful for: exploring unfamiliar datasets, drafting visualizations, writing SQL for the first time.

## Code Style

### Python Docstrings

Use reStructuredText docstrings for all functions and classes. Write detailed
docstrings whenever practical, aimed at a novice developer audience — explain
both what the code does and why.

### Planning Trade-offs

When considering trade-offs during the planning phase, ask a clarifying question
rather than making an assumption. Present the options with their implications
and ask which direction to take.

## Documentation Standards

All significant features must have a corresponding doc in `docs/`. Docs are written for **both** audiences:
- Lead with a plain-English explanation of what the feature does and why
- Follow with technical details and code examples
- Include what to do when something goes wrong

See `docs/README.md` for the index. Link new docs from there and from the main `README.md`.

## Production Deployment (Proxmox LXC)

Production runs on a Proxmox server as three LXC containers. See `deploy/proxmox/README.md` for the full step-by-step guide.

| Container | Role |
|-----------|------|
| `energy-postgres` | Native PostgreSQL 16 — isolated for resource control and backups |
| `energy-app` | Docker Compose: Prefect server + worker, pgweb |
| `energy-jupyter` | Docker Compose: Jupyter Lab |

Key files:
- `deploy/proxmox/create-lxc.sh` — run on Proxmox host to create all containers
- `deploy/proxmox/provision/postgres.sh` — native PG install + schema setup
- `deploy/proxmox/provision/app.sh` — Docker install + app services + systemd
- `deploy/proxmox/provision/jupyter.sh` — Docker install + Jupyter + systemd
- `deploy/proxmox/compose/app.yaml` — production compose (no postgres service; uses `POSTGRES_HOST`)
- `deploy/proxmox/compose/jupyter.yaml` — production compose for Jupyter
- `deploy/proxmox/.env.production.example` — production env template (includes `POSTGRES_HOST`, `ANTHROPIC_API_KEY`)

The production compose files differ from `compose.yaml` in one key way: `postgres` is not a service — it's a separate LXC reached via `POSTGRES_HOST` (static IP). All `DATABASE_URL` values substitute this variable.

## Services (Docker Compose — local dev)

| Service | Port | Purpose |
|---------|------|---------|
| postgres | 5432 | PostgreSQL 16 |
| prefect-server | 4200 | Prefect UI and API |
| prefect-worker | — | Runs scheduled ingest flows |
| jupyter | 8888 | Jupyter Lab + jupyter-ai |
| pgweb | 8080 | Postgres web UI (quick table browsing) |
| superset | 8088 | Apache Superset BI dashboard |
