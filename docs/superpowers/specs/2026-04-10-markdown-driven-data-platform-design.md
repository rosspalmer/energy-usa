# Markdown-Driven Data Platform

**Date:** 2026-04-10
**Status:** Approved
**Goal:** Establish repeatable patterns to turn markdown-defined specs into data
products, enabling Claude Code to generate, validate, transform, and visualize
data from public sources with graduated automation levels.

---

## Overview

Energy USA ingests data from public sources (starting with EIA), stores it in
Postgres, and serves it through Superset dashboards. Today all 36 datasets are
hand-coded with near-identical boilerplate. This design introduces a
markdown-spec-driven system that:

1. Defines data sources, quality expectations, domain models, and dashboards in
   markdown files
2. Uses generators (Jinja2 templates + spec parser) to produce code from those
   specs
3. Applies different automation levels per layer:
   - **Ingest: Level A (full generation)** — Claude reads spec, generates all code
   - **Validate: Level A (full generation)** — Claude generates standalone validation flows
   - **Transform: Level B (scaffold + fill)** — Claude generates skeleton, fills business logic with review
   - **Visualize: Level C (interactive build)** — Spec is a conversation starter, Claude builds iteratively

## Spec Formats

All specs live under `specs/` with a `_template.md` in each subdirectory for
bootstrapping new specs.

```
specs/
├── README.md
├── ingest/
│   ├── eia.md
│   └── _template.md
├── validate/
│   ├── eia.md
│   └── _template.md
├── transform/
│   ├── electricity.md
│   └── _template.md
└── visualize/
    ├── electricity-overview.md
    └── _template.md
```

### Ingest Spec (`specs/ingest/<source>.md`)

Describes a data source and all its datasets. One file per source.

**Required sections:**

- **Source** — client type (`rest-json`), base URL, auth mechanism (env var name),
  pagination style, rate limits
- **Datasets** — one subsection per dataset, each containing:
  - API path
  - Frequency (monthly, annual, quarterly, daily)
  - Unique key (tuple of column names for `ON CONFLICT`)
  - Column table: column name, API field name, Postgres type, required flag
  - Filters: rows to skip (e.g., national aggregates)
  - History start date

**Example dataset entry:**

```markdown
### retail_sales
- **API path**: /electricity/retail-sales
- **Frequency**: monthly
- **Unique key**: (period, stateid, sectorid)
- **Columns**:
  | Column | API field | Type | Required |
  |--------|-----------|------|----------|
  | period | period | DATE | yes |
  | stateid | stateid | TEXT | yes |
  | sectorid | sectorid | TEXT | yes |
  | revenue | revenue | NUMERIC | no |
  | sales | sales | NUMERIC | no |
  | price | price | NUMERIC | no |
  | customers | customers | NUMERIC | no |
- **Filters**: Skip rows where stateid = 'US'
- **History**: 2001-01
```

**What Claude generates from an ingest spec:**

1. `docker/postgres/init/ingest/<source>/<table>.sql` — DDL
2. `src/energy_usa/db/ingest/<source>/<table>.py` — upsert module
3. `src/energy_usa/flows/ingest/<source>/<table>.py` — Prefect flow
4. `src/energy_usa/clients/<source>.py` — API client (if new source)
5. Superset seed entry, backfill registry entry, cadence metadata

### Validate Spec (`specs/validate/<source>.md`)

Describes quality expectations per dataset. One file per source.

**Check types:**

| Check | Description | Threshold format |
|-------|-------------|------------------|
| `null_rate` | % nulls in a column | `{"max_null_pct": 5}` |
| `completeness` | Every expected dimension combo has data per period | `{"dimensions": ["stateid"], "frequency": "monthly"}` |
| `staleness` | Most recent period within N months of today | `{"max_months_behind": 3}` |
| `row_count` | Rows per period within expected range | `{"min_per_month": 40, "max_per_month": 60}` |
| `range` | Numeric values within plausible bounds | `{"column": "price", "min": 0, "max": 100}` |

**Example:**

```markdown
## retail_sales
- **Date range**: 2001-01 to present
- **Expected row count**: ~50 rows/month
- **Null tolerance**:
  | Column | Max null % |
  |--------|-----------|
  | revenue | 5 |
  | sales | 5 |
  | price | 5 |
  | customers | 10 |
- **Completeness**: Every state should have data for every month
- **Staleness**: Most recent period within 3 months of today
```

**What Claude generates:**

1. `src/energy_usa/flows/validate/<source>.py` — Prefect validation flow
2. `docker/postgres/init/ingest/<source>/audit_rules.sql` — INSERT statements
   for `quality.audit_rules` (runs at Docker init for fresh installs; for
   existing deployments, run manually or via `make validate` which upserts rules
   before checking them)
3. Postgres `CHECK` constraints where appropriate (added to the table DDL)

### Transform Spec (`specs/transform/<domain>.md`)

Describes a domain data model. One file per domain. Claude scaffolds the code
and fills in business logic; you verify join logic and column derivations.

**Required sections:**

- Domain name and purpose (plain English)
- One subsection per output table:
  - Source tables (fully qualified: `eia.retail_sales`)
  - Grain (dimensions that define a row)
  - Join logic (free text describing how sources connect)
  - Output column table: column, source, derivation logic
  - Unique key

**Example:**

```markdown
## electricity.generation_mix
Combines generation data by fuel type with emissions data to show
the environmental profile of each state's electricity generation.

- **Source tables**: eia.state_source_disposition, eia.co2_emissions
- **Grain**: state + month
- **Join logic**: Match on stateid + period
- **Output columns**:
  | Column | Source | Logic |
  |--------|--------|-------|
  | state | eia.state_source_disposition.stateid | direct |
  | period | eia.state_source_disposition.period | direct |
  | total_generation_mwh | eia.state_source_disposition.generation | sum by state+period |
  | co2_tons | eia.co2_emissions.value | sum where fuel='ALL' |
  | carbon_intensity | derived | co2_tons / total_generation_mwh |
- **Unique key**: (state, period)
```

**What Claude generates:**

1. `docker/postgres/init/transform/<domain>/<table>.sql` — DDL
2. `src/energy_usa/db/transform/<domain>/<table>.py` — SQL query + upsert (with TODO markers for review)
3. `src/energy_usa/flows/transform/<domain>.py` — Prefect flow

### Visualize Spec (`specs/visualize/<dashboard>.md`)

A conversation starter, not a generation input. Describes the dashboard's
audience, key questions, data sources, and suggested visualizations. Claude
reads this and works with you interactively to build the dashboard.

**Example:**

```markdown
# Electricity Overview Dashboard

## Audience
State energy policy analysts comparing their state against benchmarks.

## Key questions
1. How has my state's generation mix changed over 10 years?
2. How does my state's electricity price compare to neighbors?
3. What's the relationship between renewable penetration and price?

## Data sources
- transform.electricity.generation_mix
- transform.pricing.retail_by_state

## Suggested visualizations
- Stacked area: generation by fuel over time, filterable by state
- Choropleth: price by state with time slider
- Scatter: renewable % vs price, one dot per state per year
```

## Database Architecture

### Layout

Two databases on the same Postgres server. Source-as-schema in ingest,
domain-as-schema in transform.

```
Postgres Server
├── ingest (database)
│   ├── eia (schema)
│   │   ├── retail_sales
│   │   ├── electric_power_operational
│   │   ├── state_source_disposition
│   │   └── ... (36 tables)
│   ├── epa (schema, future)
│   ├── ferc (schema, future)
│   └── quality (schema)
│       ├── audit_rules
│       └── audit_results
│
└── transform (database)
    ├── electricity (schema)
    │   ├── generation_mix
    │   └── retail_by_state
    ├── fossil_fuels (schema)
    ├── emissions (schema)
    └── pricing (schema)
```

**Key decisions:**

- `quality` schema lives in the ingest database — validation flows query ingest
  tables directly with no cross-database overhead
- Transform database gets its own `TRANSFORM_DATABASE_URL` env var
- Superset connects to both databases as separate datasources

### Schema Migration (EIA Rename)

Existing `ingest.eia_*` tables migrate to `eia.*` tables. This serves as the
proving ground for the markdown-driven pattern.

**Migration steps:**

1. Create `eia` schema in the ingest database
2. For each table: `ALTER TABLE ingest.eia_retail_sales SET SCHEMA eia;` then
   `ALTER TABLE eia.eia_retail_sales RENAME TO retail_sales;`
3. Reorganize init SQL: `docker/postgres/init/ingest/eia/<table>.sql`
4. Update all db modules: table references from `ingest.eia_retail_sales` to
   `eia.retail_sales`
5. Update flow modules, Superset seed, backfill registry, Makefile, docs
6. Drop empty `ingest` schema

**Fresh installs:** Init SQL runs in the new structure. No migration needed.

**Existing deployments:** One-time migration script at
`deploy/migrations/001-rename-eia-schemas.sql`.

### Init SQL Reorganization

```
docker/postgres/init/
├── 01-create-databases.sql
├── ingest/
│   ├── 00-quality-schema.sql
│   ├── eia/
│   │   ├── 00-schema.sql
│   │   ├── retail_sales.sql
│   │   ├── electric_power_operational.sql
│   │   └── ...
│   └── epa/
│       ├── 00-schema.sql
│       └── ...
├── transform/
│   ├── electricity/
│   │   ├── 00-schema.sql
│   │   └── generation_mix.sql
│   └── ...
└── 03-run-init-scripts.sh
```

## Code Architecture

### Package Structure

```
src/energy_usa/
├── config.py                          # Adds TRANSFORM_DATABASE_URL
├── clients/
│   ├── __init__.py
│   ├── base.py                        # DataClient protocol
│   ├── eia.py                         # Current client + manager consolidated
│   └── epa.py                         # Future
│
├── db/
│   ├── __init__.py
│   ├── connection.py                  # get_connection(), shared
│   ├── period.py                      # Period normalization
│   ├── dataframe.py                   # query_to_dataframe
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── eia/
│   │   │   ├── __init__.py
│   │   │   ├── retail_sales.py
│   │   │   └── ...
│   │   └── epa/
│   ├── transform/
│   │   ├── __init__.py
│   │   ├── electricity/
│   │   │   ├── __init__.py
│   │   │   └── generation_mix.py
│   │   └── ...
│   └── quality/
│       ├── __init__.py
│       └── audit.py
│
├── flows/
│   ├── __init__.py
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── eia/
│   │   │   ├── __init__.py
│   │   │   ├── retail_sales.py
│   │   │   └── ...
│   │   └── backfill.py                # Generic: discovers flows by source
│   ├── validate/
│   │   ├── __init__.py
│   │   └── eia.py
│   ├── transform/
│   │   ├── __init__.py
│   │   └── electricity.py
│   └── date_range.py
│
└── generators/
    ├── __init__.py
    ├── parse_spec.py                  # Markdown → dataclasses
    ├── ingest.py                      # Generate ingest artifacts
    ├── validate.py                    # Generate validation artifacts
    └── templates/
        ├── db_module.py.j2
        ├── flow_module.py.j2
        ├── schema.sql.j2
        └── validate_flow.py.j2
```

### Source Client Protocol

```python
# clients/base.py
class DataClient(Protocol):
    async def fetch_dataset(
        self, dataset: str, start: str, end: str, columns: list[str]
    ) -> list[dict]: ...
```

Not a base class — a protocol. The EIA client already satisfies this. New source
clients implement the same interface. Ingest flows get the client from a
registry keyed by source name.

### Dynamic Backfill Registry

The current hardcoded `_FLOW_REGISTRY` with 36 entries is replaced by dynamic
discovery:

```python
# flows/ingest/backfill.py
def get_flow_registry(source: str) -> dict[str, Flow]:
    """Import all flow modules from flows/ingest/<source>/"""
```

Adding a new dataset and generating its flow module automatically makes it
available for backfill.

## Quality & Validation System

### Quality Schema

```sql
CREATE TABLE quality.audit_rules (
    rule_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    dataset TEXT NOT NULL,
    check_type TEXT NOT NULL,
    column_name TEXT,
    threshold JSONB NOT NULL,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE quality.audit_results (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    rule_id TEXT REFERENCES quality.audit_rules(rule_id),
    run_id TEXT NOT NULL,
    status TEXT NOT NULL,              -- pass, fail, warn, error
    measured_value JSONB,
    detail TEXT,
    checked_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_audit_results_rule
    ON quality.audit_results(rule_id, checked_at DESC);
CREATE INDEX idx_audit_results_run
    ON quality.audit_results(run_id);
```

### Validation Flow Structure

Each source gets one validation flow. Check types are generic SQL patterns; the
flow reads rules from `audit_rules` and executes them:

- `check_null_rates` — `SELECT count(*) FILTER (WHERE col IS NULL)`
- `check_completeness` — Cross-join expected dimensions x periods, LEFT JOIN
  actual, find gaps
- `check_staleness` — `SELECT max(period)`, compare to threshold
- `check_row_count` — `GROUP BY period`, compare counts to range
- `check_range` — `SELECT min(col), max(col)`, compare to bounds

### Running Validation

```bash
make validate SOURCE=eia [DATASET=retail_sales]
make audit SOURCE=eia [DATASET=retail_sales]
```

Audit results are also available as a Superset dataset for visual monitoring.

## Generator System

Development-time tool. Not a runtime dependency. Uses Jinja2 templates and a
markdown parser.

### Workflow

```
You write/edit spec → Claude reads spec → Claude runs generator → Files created → You review & commit
```

### Spec Parser

Parses markdown into typed dataclasses: `SourceSpec`, `DatasetSpec`,
`ValidationSpec`, `TransformSpec`. Each contains all fields needed by the
templates.

### Templates

Four Jinja2 templates:

- `schema.sql.j2` — Postgres DDL with primary key, indexes, comments
- `db_module.py.j2` — Upsert function with period normalization, filters, safe_numeric
- `flow_module.py.j2` — Prefect flow with async fetch + sync upsert tasks
- `validate_rules.sql.j2` — INSERT statements for `quality.audit_rules`

### Generator Commands

```bash
make generate-ingest SOURCE=... [DATASET=...]     # SQL + db module + flow
make generate-validate SOURCE=...                  # Validation flow + audit rules
make generate-transform DOMAIN=...                 # Transform scaffold
```

### What the Generator Does NOT Do

- No runtime code generation — everything is generated once and committed
- No magic imports or metaprogramming — generated code is plain Python
- No transform business logic — level B scaffolds with TODO markers
- No visualize generation — level C is interactive

## Day-to-Day Workflows

### Adding a New Data Source (Full Lifecycle)

1. **Spec authoring** — Claude reads portal docs, evaluates data size/range,
   writes `specs/ingest/<source>.md` and `specs/validate/<source>.md`
2. **Ingest generation** — `make generate-ingest SOURCE=<source>` +
   `make generate-validate SOURCE=<source>`
3. **Run and validate** — `make deploy`, `make run`, `make validate`
4. **Transform** — Write/update `specs/transform/<domain>.md`,
   `make generate-transform DOMAIN=<domain>`, review business logic
5. **Visualize** — Interactive session with Claude using
   `specs/visualize/<dashboard>.md`

### Adding a Dataset to an Existing Source

1. Claude adds dataset section to `specs/ingest/<source>.md`
2. `make generate-ingest SOURCE=<source> DATASET=<new_dataset>`
3. Review, commit, backfill

### Updating Quality Expectations

1. Edit `specs/validate/<source>.md`
2. Regenerate audit rules SQL
3. `make validate SOURCE=<source>`

## Documentation Updates

The following documentation must be updated as part of implementation to reflect
the new architecture:

### CLAUDE.md
- **Architecture section**: Update data flow diagram to show ingest → validate → transform → visualize pipeline
- **Key Components**: Restructure to reflect `clients/`, nested `db/ingest/`, `db/transform/`, `db/quality/`, nested `flows/`, and `generators/`
- **Databases table**: Add `transform` database with `TRANSFORM_DATABASE_URL`, add `quality` schema description
- **Ingest Patterns**: Document the markdown-spec-driven workflow and generator commands
- **Common Commands**: Add `make generate-ingest`, `make generate-validate`, `make generate-transform`, `make validate`, `make audit`
- **Code Style**: Add spec format conventions (markdown table format, required sections)

### README.md
- Update project description to reflect the markdown-driven development pattern
- Update architecture overview and data flow
- Add section on specs (`specs/` directory purpose and structure)
- Update quick-start commands to include generation workflow

### docs/README.md (index)
- Add entries for this design spec
- Add entries for any new guides created during implementation (e.g., writing specs, using generators)

### docs/ingest-flows.md
- Update to reflect new directory structure (`flows/ingest/<source>/`)
- Document generator workflow: spec → generate → review → commit → deploy → backfill
- Update table/schema names from `ingest.eia_*` to `eia.*`

### docs/getting-started.md
- Update setup instructions for new `TRANSFORM_DATABASE_URL` env var
- Update first-run walkthrough to use new schema names
- Add generator quick-start

### docs/data-analysis.md
- Update table references from `ingest.eia_*` to `eia.*`
- Add transform layer tables as query targets
- Add quality audit tables for data quality exploration

### New Documentation
- `docs/writing-specs.md` — How to write ingest, validate, transform, and visualize specs. Targeted at both audiences: data engineers authoring specs and industry professionals understanding what the specs mean.
- `specs/README.md` — Quick reference for spec formats, conventions, and which automation level applies to each layer.

## What Changes vs. What Stays

| Stays the same | Changes |
|----------------|---------|
| `make up/down/logs/deploy/run` | Table names: `ingest.eia_*` → `eia.*` |
| Prefect as orchestrator | Flat dirs → nested by source/domain |
| Postgres as storage | New `specs/` directory |
| Superset for dashboards | New `transform` database |
| Docker Compose local dev | New `quality` schema |
| Proxmox production deploy | New `generators/` package |
| DuckDB for ad-hoc analysis | New `clients/` package (replaces `eia/`) |
| jupyter-ai integration | New Makefile targets: generate, validate, audit |
| `config.py` pydantic settings | `config.py` adds `TRANSFORM_DATABASE_URL` |
