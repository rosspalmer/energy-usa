# Evidence Docs — Design Spec

**Date:** 2026-04-16
**Status:** Design (pre-implementation)
**Companion plan:** _to be written via `superpowers:writing-plans`_

## Overview

Add [Evidence.dev](https://docs.evidence.dev/) to the Energy USA stack as a
narrative-first complement to Superset. Evidence turns markdown files with
embedded SQL into interactive, filterable data reports. Where Superset is
optimized for ad-hoc exploration, Evidence is optimized for curated
walkthroughs — "here is what this table means, with live numbers mixed into
prose."

The first deliverable is a single example report, `state-monthly-balance`,
that breaks down the components and totals of
`electricity.state_monthly_balance` and is filterable by state.

## Goals

1. Run Evidence as a first-class Docker service alongside Superset; `make up`
   gets both.
2. Support a hand-authored markdown workflow for Evidence pages (no code
   generation at this stage).
3. Produce one polished example report that demonstrates the value proposition
   — text narrative interleaved with SQL-driven charts and templated values.
4. Document the workflow clearly enough that a non-technical user can follow
   along and add their own report.

## Non-goals

- Replacing Superset. The two tools coexist with distinct roles.
- Publishing the built static site anywhere. `make evidence-build` exists as
  an entry point but deployment is deferred.
- Authentication. The Evidence dev server has no built-in auth; we treat it
  as an internal dev tool only.
- Code generation from a separate spec file. Evidence pages are markdown
  already; adding a generator would hide the feature that makes them readable.
  Revisit if/when a pattern emerges across many reports.
- Production deployment via the Proxmox path. Deferred to a later spec.
- More than one example report in this spec.

## Architecture

```
┌─────────────┐   SQL at dev/build-time   ┌──────────────┐
│ Postgres    │◀───────────────────────── │ Evidence     │
│ transform.* │                           │ (Node :3000) │
│ electricity │                           │ hand-authored│
└─────────────┘                           │   markdown   │
                                          └──────┬───────┘
                                                 │ hot-reloaded SPA
                                                 ▼
                                         Browser: chart
                                         components + text
                                         with {inputs.x.value}
                                         and {query_name[0].col}
                                         interpolation
```

- **Database:** Evidence reads from the `transform` Postgres DB using the
  official `@evidence-dev/postgres` source plugin. Credentials are passed
  through compose-level env vars, identical to how Superset is wired.
- **Dev server:** Evidence's `npm run dev` runs inside the container and
  serves on port 3000. SQL query results refresh on save.
- **Reactivity:** pages declare `<Dropdown>` / `<DateRange>` inputs bound to
  names like `inputs.state`; SQL blocks read those values via
  `${inputs.state.value}` templating, so changing the dropdown re-executes all
  queries that reference it. Scalar values from SQL results are spliced into
  prose using `{query_name[0].column}` syntax.
- **Build output:** `npm run build` produces a static site in
  `evidence/build/`; exposed via `make evidence-build`. Not deployed anywhere
  yet.

## Repo structure

```
evidence/                                # Evidence project root (checked in)
├── package.json                         # pinned evidence deps
├── package-lock.json
├── svelte.config.js                     # default from `npx evidence create`
├── evidence.plugins.yaml                # registers @evidence-dev/postgres
├── sources/
│   └── transform_db/
│       ├── connection.yaml              # reads ${POSTGRES_*} env vars
│       └── queries/                     # optional shared .sql snippets
└── pages/
    ├── index.md                         # landing page — links to reports
    └── electricity/
        └── state-monthly-balance.md     # the example report

Dockerfile.evidence                      # node:20-alpine + evidence install
compose.yaml                             # + evidence service
Makefile                                 # + evidence, evidence-build, evidence-logs
docs/
└── evidence.md                          # how-to guide (both audiences)
```

Gitignored: `evidence/node_modules/`, `evidence/build/`, `evidence/.evidence/`.

## Docker & compose

`Dockerfile.evidence`:

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY evidence/package.json evidence/package-lock.json ./
RUN npm ci
COPY evidence/ ./
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

New service in `compose.yaml`:

```yaml
evidence:
  build: { context: ., dockerfile: Dockerfile.evidence }
  environment:
    POSTGRES_HOST: postgres
    POSTGRES_PORT: 5432
    POSTGRES_DATABASE: transform
    POSTGRES_USER: ${POSTGRES_USER:-energy}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-energy}
  volumes:
    - ./evidence:/app             # hot reload
    - evidence_node_modules:/app/node_modules
  ports:
    - "3000:3000"
  depends_on:
    postgres:
      condition: service_healthy
```

And a named volume entry: `evidence_node_modules: {}`.

`evidence/sources/transform_db/connection.yaml`:

```yaml
name: transform_db
type: postgres
options:
  host: $POSTGRES_HOST
  port: $POSTGRES_PORT
  database: $POSTGRES_DATABASE
  user: $POSTGRES_USER
  password: $POSTGRES_PASSWORD
  ssl: false
```

No new `.env.example` entries are required; Evidence reuses the existing
`POSTGRES_USER` and `POSTGRES_PASSWORD` values.

## Makefile targets

- `make evidence` — start just the evidence service plus its dependencies
  (`docker compose up -d postgres evidence`).
- `make evidence-build` — run the build step inside the container to produce
  `evidence/build/`.
- `make evidence-logs` — tail the evidence container logs.

`make help` is updated to include these.

## Example report: `pages/electricity/state-monthly-balance.md`

The report has seven sections, driven by a state dropdown and a date-range
input at the top. Each chart is followed by a short narrative summary that
interpolates scalar values from a SQL query — this mix of chart and templated
prose is the core pattern we want the example to teach.

1. **Intro + KPI tiles.** A markdown paragraph citing the latest period and
   headline numbers, followed by four `<BigValue>` tiles: total generation,
   net interstate trade, total consumption, estimated losses.
2. **Generation mix over time.** Stacked `<AreaChart>` over the per-fuel
   columns (`gen_coal_mwh`, `gen_natural_gas_mwh`, `gen_nuclear_mwh`,
   `gen_hydro_mwh`, `gen_solar_mwh`, `gen_wind_mwh`, `gen_geothermal_mwh`,
   `gen_biomass_mwh`, `gen_petroleum_mwh`). Narrative summary mentions top
   fuel and renewable share trend.
3. **Fossil vs renewable vs nuclear.** Simpler stacked `<AreaChart>` of the
   three derived rollups (`gen_fossil_mwh`, `gen_renewable_mwh`,
   `gen_nuclear_mwh`). Narrative summary shows current shares and year-over-
   year renewable trend.
4. **Supply & trade.** Multi-line chart overlaying `total_supply_mwh`,
   `international_imports_mwh`, `international_exports_mwh`, and
   `net_interstate_trade_mwh`. Narrative describes whether the state is a net
   importer/exporter and quantifies international trade.
5. **Consumption by sector.** Stacked `<AreaChart>` over the
   `consumption_residential_mwh`, `_commercial_mwh`, `_industrial_mwh`,
   `_transportation_mwh`, `_other_mwh` columns. Narrative identifies the
   largest sector and notes seasonal variation.
6. **Balance check.** Two-series line chart plotting supply side
   (`gen_total_mwh + net_interstate_trade_mwh + international_imports_mwh -
   international_exports_mwh`) against demand side (`consumption_total_mwh +
   estimated_losses_mwh`). Narrative reports the average residual percentage
   as a data-quality sanity check.
7. **Recent months data table.** Evidence `<DataTable>` with `search=true
   sort=true` over the last 24 months for the selected state, showing the
   main rollup columns.

All queries filter on `WHERE state = '${inputs.state.value}'` and respect
the date-range input where applicable.

## Documentation

New file: `docs/evidence.md`, written for both audiences.

Sections:
1. What Evidence is (plain English, one paragraph).
2. When to use Evidence vs Superset (decision table).
3. Running it (`make up`, `localhost:3000`).
4. Anatomy of a page — walkthrough of `state-monthly-balance.md`, explaining
   fenced SQL blocks, `<Chart>` components, `<Dropdown>` inputs, and
   `{query[0].col}` interpolation.
5. Adding a new report — copy the example, edit queries, add sections.
6. Filters and reactive values — how inputs drive queries and text.
7. Troubleshooting — UI query errors, Postgres connection failures, hot
   reload issues.

Updates to existing docs:
- `docs/README.md` — add an Evidence row to the guides table.
- `README.md` — mention Evidence alongside Superset in the architecture
  section and the services list.
- `CLAUDE.md` — add an `evidence | 3000 | Evidence.dev narrative data docs`
  row to the services table, and a short pointer to `docs/evidence.md`.

## Verification

No automated tests — Evidence is a static-site frontend. Manual checks:

1. `make up` brings the full stack up; `docker compose ps` reports
   `evidence` as healthy.
2. `http://localhost:3000` loads the index page and links to the report.
3. `http://localhost:3000/electricity/state-monthly-balance` renders all
   seven sections with the default state (CA) and shows real numbers.
4. Changing the state dropdown re-runs queries and updates every chart and
   every templated number in the narrative.
5. Editing `evidence/pages/electricity/state-monthly-balance.md` on the host
   triggers a hot reload in the browser within a few seconds.
6. `make evidence-build` completes successfully and writes
   `evidence/build/index.html`.

## Risks & open questions

- **First-boot time.** `npm ci` in the Docker build can take a minute or two.
  Acceptable for this phase; revisit if it becomes painful.
- **Evidence version pinning.** Pin Evidence deps in `package.json` and
  `package-lock.json`. Upgrades are opt-in.
- **Node volume mount collision.** Mounting `./evidence:/app` would clobber
  `/app/node_modules`. We work around this with a named volume
  (`evidence_node_modules`) mounted on top. Standard Node-in-Docker pattern
  but worth documenting in `docs/evidence.md`.
- **Deployment.** Out of scope for this spec but will need a follow-up —
  likely `make evidence-build` + serving `evidence/build/` from a static
  host, or a separate compose file for the Proxmox `energy-app` container.