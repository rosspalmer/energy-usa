# Evidence Docs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up Evidence.dev as a Docker-based complement to Superset, produce one example narrative report for `electricity.state_monthly_balance` filterable by state, and wire up build/publish targets so reports are shareable as static bundles.

**Architecture:** Evidence runs as a Node-based service in `compose.yaml` on port 3000. It connects to the `transform` Postgres database via the `@evidence-dev/postgres` source plugin. Pages are hand-authored markdown with embedded SQL and `<Chart>` / `<BigValue>` components. `make evidence-build` produces a static SPA in `evidence/build/`; `make evidence-publish DEST=…` syncs it to a local directory or s3:// URI for sharing.

**Tech Stack:** Evidence.dev (SvelteKit static-site generator), Node 20, Docker Compose, Postgres 16, Make, bash, rsync, optionally `aws s3 sync`.

**Testing approach:** Evidence is a static-site frontend with no traditional unit test harness. Verification is manual and uses browser checks, `docker compose ps`, `curl`, and filesystem assertions. Each task ends with explicit verification commands and expected output.

**Reference spec:** `docs/superpowers/specs/2026-04-16-evidence-docs-design.md`.

**Prerequisites before starting:**
- Docker Desktop running
- `.env` has `POSTGRES_USER`, `POSTGRES_PASSWORD`, `EIA_API_KEY` set
- Existing stack can boot: `make up` succeeds
- `electricity.state_monthly_balance` is populated. If not: `make transform DOMAIN=electricity` after `make up` and a backfill of `state_source_disposition`, `electric_power_operational`, `retail_sales`.

---

## Task 1: Scaffold the Evidence project

**Files:**
- Create: `evidence/package.json`
- Create: `evidence/package-lock.json`
- Create: `evidence/evidence.config.yaml` (combined plugins + theme config in current Evidence)
- Create: `evidence/pages/index.md` (placeholder; Task 7 replaces it)
- Create: `evidence/README.md`, `evidence/.npmrc`, `evidence/.gitignore`, `evidence/.vscode/extensions.json` (standard scaffold files)
- Modify: `.gitignore`

We clone the official Evidence starter template with `degit` so the dependency set and scaffold files stay in sync with current Evidence. Then we trim the demo content and commit only the skeleton.

> **Note on the scaffold command.** Current Evidence (v40+) ships a single `evidence.config.yaml` (no separate `svelte.config.js` or `evidence.plugins.yaml` — Evidence regenerates those at runtime into `.evidence/template/`). The plan was originally written against an older layout; this reflects the current reality.

- [ ] **Step 1: Clone the Evidence starter template**

Run from the repo root:

```bash
npx --yes degit evidence-dev/template evidence
```

Expected: `degit` clones the template into `evidence/` (tracked files only, no `.git/`). If `npx` or `git` is unavailable on the host, run inside a Node container:

```bash
docker run --rm -v "$PWD":/work -w /work node:20-alpine \
  sh -c "apk add --no-cache git && npx --yes degit evidence-dev/template evidence"
```

- [ ] **Step 2: Remove demo content, keep only skeleton**

Delete every file under `evidence/pages/` except we'll create a minimal placeholder. Also delete any sample `sources/` directories that the scaffold created so we start clean.

```bash
rm -rf evidence/pages/*
rm -rf evidence/sources/*
mkdir -p evidence/pages evidence/sources
```

Create `evidence/pages/index.md` with placeholder content (Task 7 replaces it):

```markdown
---
title: Energy USA — Evidence
---

Scaffold complete. Reports will be added here.
```

- [ ] **Step 3: Add Evidence-specific gitignore entries**

Append to the top-level `.gitignore`:

```
# Evidence
evidence/node_modules/
evidence/build/
evidence/.evidence/template/
evidence/.evidence/meta/
evidence/static/data/
```

Note the `.evidence/template` and `.evidence/meta` scoping: these are the
generated subdirs. We deliberately leave `.evidence/customization/`
trackable because it holds user-authored format presets.

Verify `.gitignore` now contains those lines:

```bash
grep -E "evidence/(node_modules|build|\.evidence/(template|meta)|static/data)" .gitignore
```

Expected: five matching lines printed.

- [ ] **Step 4: Verify the scaffold boots locally**

Optional but strongly recommended. From `evidence/`:

```bash
cd evidence && npm install && npm run sources && npm run dev -- --host 0.0.0.0 &
sleep 15 && curl -sf http://localhost:3000 | head -n 5
kill %1
cd ..
```

Expected: `curl` returns HTML (Evidence landing page). If it fails, inspect `npm install` / `npm run dev` output for errors before proceeding. Note: `npm run sources` will warn "no sources configured" — that's expected until Task 2.

- [ ] **Step 5: Commit**

```bash
git add evidence/ .gitignore
git commit -m "scaffold Evidence.dev project"
```

---

## Task 2: Configure the Postgres datasource

**Files:**
- Create: `evidence/sources/transform_db/connection.yaml`
- Create: `evidence/sources/transform_db/queries/.gitkeep`

Evidence v2+ reads sources from `evidence/sources/<name>/connection.yaml`. Values prefixed with `$` are pulled from env vars at build time.

- [ ] **Step 1: Create the connection file**

Write `evidence/sources/transform_db/connection.yaml`:

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

- [ ] **Step 2: Add a `queries/` directory marker**

Evidence tolerates a missing `queries/` directory but we keep one to make the shared-query convention discoverable. Create an empty `.gitkeep`:

```bash
mkdir -p evidence/sources/transform_db/queries
touch evidence/sources/transform_db/queries/.gitkeep
```

- [ ] **Step 3: Commit**

```bash
git add evidence/sources/transform_db/
git commit -m "add Evidence transform_db Postgres source"
```

---

## Task 3: Add the Dockerfile

**Files:**
- Create: `Dockerfile.evidence`

- [ ] **Step 1: Write `Dockerfile.evidence`**

```dockerfile
# Evidence.dev dev server. Built as part of the main compose stack.
# The image is intentionally thin: node_modules are installed once at build
# time, then the project source is bind-mounted in compose so edits on the
# host hot-reload inside the container.
FROM node:20-alpine

WORKDIR /app

# Install deps from package-lock for reproducibility. --legacy-peer-deps
# works around an upstream ERESOLVE between Evidence's typescript peer and
# svelte2tsx (known Evidence issue as of v40.x).
COPY evidence/package.json evidence/package-lock.json ./
RUN npm ci --legacy-peer-deps

# Seed the rest of the project so first-run before the bind mount works.
COPY evidence/ ./

EXPOSE 3000

# Dev mode keeps hot reload on the bind-mounted source.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

- [ ] **Step 2: Verify it builds standalone**

```bash
docker build -f Dockerfile.evidence -t energy-evidence:test .
```

Expected: build succeeds. `npm ci` may take 1–2 minutes on first run.

- [ ] **Step 3: Remove the test tag**

```bash
docker rmi energy-evidence:test
```

- [ ] **Step 4: Commit**

```bash
git add Dockerfile.evidence
git commit -m "add Dockerfile for Evidence.dev service"
```

---

## Task 4: Wire Evidence into compose.yaml

**Files:**
- Modify: `compose.yaml` (add service block + named volume)

The `./evidence:/app` bind mount gives us hot reload, but it would also clobber `/app/node_modules` installed by the Dockerfile. The `evidence_node_modules` named volume mounts on top and preserves the installed modules.

- [ ] **Step 1: Append the `evidence` service**

Insert the following block into `compose.yaml` immediately after the `superset` service block (just before the `volumes:` section on line 137, taking into account the file may have shifted):

```yaml
  evidence:
    build:
      context: .
      dockerfile: Dockerfile.evidence
    environment:
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      POSTGRES_DATABASE: transform
      POSTGRES_USER: ${POSTGRES_USER:-energy}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-energy}
    volumes:
      - ./evidence:/app
      - evidence_node_modules:/app/node_modules
    ports:
      - "3000:3000"
    depends_on:
      postgres:
        condition: service_healthy
```

- [ ] **Step 2: Add the named volume**

Change the `volumes:` block at the bottom of the file from:

```yaml
volumes:
  postgres_data: {}
  prefect_results: {}
```

to:

```yaml
volumes:
  postgres_data: {}
  prefect_results: {}
  evidence_node_modules: {}
```

- [ ] **Step 3: Validate compose configuration**

```bash
docker compose config --services
```

Expected: prints a list that includes `evidence`.

```bash
docker compose config > /tmp/compose-rendered.yaml && grep -A 3 "evidence_node_modules" /tmp/compose-rendered.yaml
```

Expected: the volume shows up under the top-level `volumes:` block.

- [ ] **Step 4: Bring the service up and smoke-test it**

```bash
docker compose up -d postgres evidence
sleep 30
curl -sf -o /dev/null -w "%{http_code}\n" http://localhost:3000
```

Expected: `200`. If `000` or non-200, tail the logs:

```bash
docker compose logs evidence --tail 80
```

Common issues: port 3000 in use, or `npm run dev` still starting (wait another 20s and retry).

- [ ] **Step 5: Stop the services**

```bash
docker compose down
```

- [ ] **Step 6: Commit**

```bash
git add compose.yaml
git commit -m "add Evidence service to Docker Compose stack"
```

---

## Task 5: Add `evidence`, `evidence-build`, and `evidence-logs` Makefile targets

**Files:**
- Modify: `Makefile`

- [ ] **Step 1: Extend the `.PHONY` declaration**

Change the existing `.PHONY` line to include the new targets. Find:

```make
.PHONY: help up down logs deploy \
        backfill \
        jupyter \
        export \
        generate-ingest \
        validate audit generate-validate \
        transform \
        dashboard-list dashboard-export dashboard-import
```

Replace with:

```make
.PHONY: help up down logs deploy \
        backfill \
        jupyter \
        export \
        generate-ingest \
        validate audit generate-validate \
        transform \
        dashboard-list dashboard-export dashboard-import \
        evidence evidence-build evidence-logs evidence-publish
```

- [ ] **Step 2: Add the Evidence target section at the bottom of the file**

Append below the dashboards section:

```make
# ── Evidence docs ─────────────────────────────────────────────────────────────
# Evidence turns markdown + SQL into interactive static reports. Dev server at
# http://localhost:3000 once the stack is up. See docs/evidence.md.
#
# Examples:
#   make evidence                          # start just postgres + evidence
#   make evidence-build                    # build static site to evidence/build/
#   make evidence-logs                     # tail the container log
#   make evidence-publish DEST=/tmp/share  # sync build to a directory
#   make evidence-publish DEST=s3://bucket/path/

DEST ?= exports/evidence-build/

evidence:  ## Start just the Evidence service (+ postgres dependency)
	docker compose up -d postgres evidence
	@echo "Evidence available at http://localhost:3000"

evidence-build:  ## Build Evidence static site to evidence/build/
	docker compose run --rm evidence npm run build
	@echo "Built static site at evidence/build/"

evidence-logs:  ## Tail the evidence container logs
	docker compose logs -f evidence
```

(The `evidence-publish` target is added in Task 6.)

- [ ] **Step 3: Verify help renders the new targets**

```bash
make help | grep evidence
```

Expected output includes:

```
  evidence               Start just the Evidence service (+ postgres dependency)
  evidence-build         Build Evidence static site to evidence/build/
  evidence-logs          Tail the evidence container logs
```

- [ ] **Step 4: Verify `make evidence` works**

```bash
make evidence
sleep 20
curl -sf -o /dev/null -w "%{http_code}\n" http://localhost:3000
```

Expected: `200`.

- [ ] **Step 5: Verify `make evidence-build` works**

```bash
make evidence-build
ls evidence/build/index.html
```

Expected: `evidence/build/index.html` exists. The build may take 30–60 seconds.

- [ ] **Step 6: Stop the stack**

```bash
docker compose down
```

- [ ] **Step 7: Commit**

```bash
git add Makefile
git commit -m "add Makefile targets for Evidence dev, build, and logs"
```

---

## Task 6: Add `evidence-publish` target

**Files:**
- Modify: `Makefile`

`evidence-publish DEST=<path>` copies the latest build to a destination for sharing. Local paths use `rsync`; `s3://` destinations use `aws s3 sync`. Missing builds trigger `make evidence-build` first.

- [ ] **Step 1: Append the `evidence-publish` target**

Add to the end of the `# ── Evidence docs ──` section in `Makefile`:

```make
evidence-publish:  ## Sync evidence/build/ to DEST (local dir or s3:// URI)
	@if [ ! -f evidence/build/index.html ]; then \
	    echo "evidence/build missing — running evidence-build first"; \
	    $(MAKE) evidence-build; \
	fi
	@case "$(DEST)" in \
	  s3://*) \
	    command -v aws >/dev/null 2>&1 || { \
	      echo "error: aws CLI not found on PATH; install it or pick a local DEST"; \
	      exit 1; \
	    }; \
	    echo "Publishing to $(DEST) via aws s3 sync"; \
	    aws s3 sync evidence/build/ "$(DEST)" --delete ;; \
	  *) \
	    mkdir -p "$(DEST)"; \
	    echo "Publishing to $(DEST) via rsync"; \
	    rsync -av --delete evidence/build/ "$(DEST)" ;; \
	esac
	@echo "Published to $(DEST)"
```

- [ ] **Step 2: Verify `make help` shows the target**

```bash
make help | grep evidence-publish
```

Expected: a row for `evidence-publish`.

- [ ] **Step 3: Verify local-path publish**

```bash
rm -rf /tmp/evidence-share
make evidence-publish DEST=/tmp/evidence-share
ls /tmp/evidence-share/index.html
```

Expected: `/tmp/evidence-share/index.html` exists.

- [ ] **Step 4: Verify `s3://` detection fails cleanly without `aws`**

Only run this if you don't have AWS credentials configured — skip otherwise.

```bash
PATH=/usr/bin:/bin make evidence-publish DEST=s3://fake-bucket/path/ || echo "exited non-zero as expected"
```

Expected: error line "aws CLI not found…" and non-zero exit.

- [ ] **Step 5: Commit**

```bash
git add Makefile
git commit -m "add evidence-publish Makefile target"
```

---

## Task 7: Write the landing page (`evidence/pages/index.md`)

**Files:**
- Modify: `evidence/pages/index.md`

- [ ] **Step 1: Overwrite the placeholder**

Replace the content of `evidence/pages/index.md` with:

```markdown
---
title: Energy USA — Data Reports
---

Narrative reports backed by the Energy USA transform database. These pages
are hand-authored markdown with embedded SQL — every number and chart on
every page refreshes the moment the underlying data changes.

## Reports

- [State Monthly Electricity Balance](/electricity/state-monthly-balance) —
  generation, trade, and consumption for a single state, month by month.
  Filterable by state and date range.

## Adding a report

See [docs/evidence.md](https://github.com/) for the workflow. Short version:
copy an existing page in `evidence/pages/`, rewrite the SQL queries and
narrative, and save — the dev server hot-reloads automatically.
```

- [ ] **Step 2: Verify it renders**

With the stack up (`make evidence`):

```bash
curl -sf http://localhost:3000 | grep -o "State Monthly Electricity Balance"
```

Expected: the string prints.

- [ ] **Step 3: Commit**

```bash
git add evidence/pages/index.md
git commit -m "write Evidence landing page"
```

---

## Task 8: State-monthly-balance page — inputs + intro + KPI tiles

**Files:**
- Create: `evidence/pages/electricity/state-monthly-balance.md`

This task lays down the page scaffold: title, filters, the first few queries, the intro paragraph with interpolated values, and four `<BigValue>` tiles. Later tasks append additional sections to the same file.

- [ ] **Step 1: Create the page**

Write `evidence/pages/electricity/state-monthly-balance.md`:

````markdown
---
title: State Monthly Electricity Balance
---

This report breaks down the supply and demand balance for a single state
using monthly data from EIA. Use the dropdown to pick a state; every chart
and headline number updates in place.

<Dropdown
  name=state
  data={states}
  value=state
  label=state
  title="State"
  defaultValue="CA"
/>

<DateRange
  name=range
  title="Date range"
  defaultValue="Last 5 Years"
/>

```sql states
select distinct state
from electricity.state_monthly_balance
order by state
```

```sql latest
select *
from electricity.state_monthly_balance
where state = '${inputs.state.value}'
order by period desc
limit 1
```

In **{inputs.state.value}**, the most recent month on record is
**{latest[0].period}**. The state generated
**{latest[0].gen_total_mwh}** MWh of electricity that month. Fossil sources
contributed **{latest[0].gen_fossil_mwh}** MWh, renewables
**{latest[0].gen_renewable_mwh}** MWh, and nuclear
**{latest[0].gen_nuclear_mwh}** MWh. Retail customers consumed
**{latest[0].consumption_total_mwh}** MWh.

<BigValue
  data={latest}
  value=gen_total_mwh
  title="Total generation (MWh)"
  fmt="#,##0"
/>

<BigValue
  data={latest}
  value=net_interstate_trade_mwh
  title="Net interstate trade (MWh)"
  fmt="#,##0"
/>

<BigValue
  data={latest}
  value=consumption_total_mwh
  title="Total consumption (MWh)"
  fmt="#,##0"
/>

<BigValue
  data={latest}
  value=estimated_losses_mwh
  title="Estimated losses (MWh)"
  fmt="#,##0"
/>
````

- [ ] **Step 2: Verify the page loads**

With the stack up (`make evidence` and postgres healthy):

```bash
sleep 15
curl -sf http://localhost:3000/electricity/state-monthly-balance | grep -o "State Monthly Electricity Balance"
```

Expected: the string prints.

Then open `http://localhost:3000/electricity/state-monthly-balance` in a
browser. You should see: the state dropdown defaulting to CA, the date
range input, one paragraph of text with real numbers interpolated, and
four BigValue tiles. If numbers show as `undefined`, the
`state_monthly_balance` table has no rows for CA — backfill and run
`make transform DOMAIN=electricity`.

- [ ] **Step 3: Commit**

```bash
git add evidence/pages/electricity/state-monthly-balance.md
git commit -m "add state-monthly-balance scaffold with filters and KPIs"
```

---

## Task 9: Generation mix over time (section 2)

**Files:**
- Modify: `evidence/pages/electricity/state-monthly-balance.md`

Append a section plotting monthly generation by fuel type, followed by a narrative summary that pulls current shares and top-fuel identification from SQL.

- [ ] **Step 1: Append the section**

Add to the end of the file:

````markdown

## Generation mix over time

Stacked area chart of monthly generation (MWh) by fuel type.

```sql gen_mix
select
  period,
  gen_coal_mwh          as coal,
  gen_natural_gas_mwh   as natural_gas,
  gen_nuclear_mwh       as nuclear,
  gen_hydro_mwh         as hydro,
  gen_solar_mwh         as solar,
  gen_wind_mwh          as wind,
  gen_geothermal_mwh    as geothermal,
  gen_biomass_mwh       as biomass,
  gen_petroleum_mwh     as petroleum
from electricity.state_monthly_balance
where state = '${inputs.state.value}'
  and period between '${inputs.range.start}' and '${inputs.range.end}'
order by period
```

<AreaChart
  data={gen_mix}
  x=period
  y={["coal","natural_gas","nuclear","hydro","solar","wind","geothermal","biomass","petroleum"]}
  type=stacked
  yFmt="#,##0"
  title="Generation by fuel type"
/>

```sql gen_mix_summary
with ranked as (
  select
    case
      when gen_coal_mwh        = gen_total_mwh then 'coal'
      when gen_natural_gas_mwh = gen_total_mwh then 'natural gas'
      when gen_nuclear_mwh     = gen_total_mwh then 'nuclear'
      when gen_hydro_mwh       = gen_total_mwh then 'hydro'
      when gen_solar_mwh       = gen_total_mwh then 'solar'
      when gen_wind_mwh        = gen_total_mwh then 'wind'
      else (
        select fuel from (values
          ('coal',        gen_coal_mwh),
          ('natural gas', gen_natural_gas_mwh),
          ('nuclear',     gen_nuclear_mwh),
          ('hydro',       gen_hydro_mwh),
          ('solar',       gen_solar_mwh),
          ('wind',        gen_wind_mwh),
          ('geothermal',  gen_geothermal_mwh),
          ('biomass',     gen_biomass_mwh),
          ('petroleum',   gen_petroleum_mwh)
        ) as f(fuel, amt)
        order by amt desc nulls last
        limit 1
      )
    end as top_fuel,
    round(100.0 * gen_renewable_mwh / nullif(gen_total_mwh, 0), 1) as renewable_share,
    period
  from electricity.state_monthly_balance
  where state = '${inputs.state.value}'
  order by period desc
  limit 1
)
select * from ranked
```

In the most recent month, the largest single fuel source in
**{inputs.state.value}** was **{gen_mix_summary[0].top_fuel}**. Renewables
supplied **{gen_mix_summary[0].renewable_share}%** of generation.
````

- [ ] **Step 2: Verify the chart renders**

With hot reload active, refresh `http://localhost:3000/electricity/state-monthly-balance`. Confirm:
- The "Generation mix over time" heading appears.
- A stacked area chart renders with nine fuel series.
- The narrative under the chart has no `undefined` values.

If a series doesn't render, check the column name in `docker/postgres/init/transform/electricity/state_monthly_balance.sql` matches.

- [ ] **Step 3: Commit**

```bash
git add evidence/pages/electricity/state-monthly-balance.md
git commit -m "add generation mix section to state-monthly-balance"
```

---

## Task 10: Fossil vs renewable vs nuclear rollup (section 3)

**Files:**
- Modify: `evidence/pages/electricity/state-monthly-balance.md`

- [ ] **Step 1: Append the section**

Add to the end of the file:

````markdown

## Fossil vs renewable vs nuclear

A simpler view of the same data grouped into three derived rollups.

```sql gen_rollup
select
  period,
  gen_fossil_mwh    as fossil,
  gen_renewable_mwh as renewable,
  gen_nuclear_mwh   as nuclear
from electricity.state_monthly_balance
where state = '${inputs.state.value}'
  and period between '${inputs.range.start}' and '${inputs.range.end}'
order by period
```

<AreaChart
  data={gen_rollup}
  x=period
  y={["fossil","renewable","nuclear"]}
  type=stacked
  yFmt="#,##0"
  title="Generation rollup"
/>

```sql rollup_summary
with latest as (
  select *
  from electricity.state_monthly_balance
  where state = '${inputs.state.value}'
  order by period desc
  limit 1
),
yoy as (
  select gen_renewable_mwh
  from electricity.state_monthly_balance
  where state = '${inputs.state.value}'
    and period = (select period - interval '1 year' from latest)
)
select
  round(100.0 * latest.gen_fossil_mwh    / nullif(latest.gen_total_mwh,0), 1) as fossil_share,
  round(100.0 * latest.gen_renewable_mwh / nullif(latest.gen_total_mwh,0), 1) as renewable_share,
  round(100.0 * latest.gen_nuclear_mwh   / nullif(latest.gen_total_mwh,0), 1) as nuclear_share,
  round(100.0 * (latest.gen_renewable_mwh - yoy.gen_renewable_mwh) / nullif(yoy.gen_renewable_mwh, 0), 1) as renewable_yoy_pct
from latest, yoy
```

Fossil fuels currently supply **{rollup_summary[0].fossil_share}%** of
generation, renewables **{rollup_summary[0].renewable_share}%**, and nuclear
**{rollup_summary[0].nuclear_share}%**. Renewable output is
**{rollup_summary[0].renewable_yoy_pct}%** year-over-year.
````

- [ ] **Step 2: Verify**

Refresh the page. Confirm a three-series stacked area chart and a narrative with three percentages and a year-over-year delta.

- [ ] **Step 3: Commit**

```bash
git add evidence/pages/electricity/state-monthly-balance.md
git commit -m "add fossil vs renewable vs nuclear rollup section"
```

---

## Task 11: Supply & trade (section 4)

**Files:**
- Modify: `evidence/pages/electricity/state-monthly-balance.md`

- [ ] **Step 1: Append the section**

Add to the end of the file:

````markdown

## Supply & trade

Where the state's electricity comes from when generation alone doesn't
balance demand. International imports and exports are typically small;
interstate trade is usually the bigger lever.

```sql supply_trade
select
  period,
  total_supply_mwh              as total_supply,
  international_imports_mwh     as intl_imports,
  international_exports_mwh     as intl_exports,
  net_interstate_trade_mwh      as net_interstate
from electricity.state_monthly_balance
where state = '${inputs.state.value}'
  and period between '${inputs.range.start}' and '${inputs.range.end}'
order by period
```

<LineChart
  data={supply_trade}
  x=period
  y={["total_supply","intl_imports","intl_exports","net_interstate"]}
  yFmt="#,##0"
  title="Supply and trade (MWh)"
/>

```sql trade_summary
with latest as (
  select *
  from electricity.state_monthly_balance
  where state = '${inputs.state.value}'
  order by period desc
  limit 1
)
select
  case when net_interstate_trade_mwh < 0 then 'importer' else 'exporter' end as direction,
  abs(net_interstate_trade_mwh) as net_interstate_abs,
  international_imports_mwh      as intl_imports,
  international_exports_mwh      as intl_exports
from latest
```

In the most recent month, **{inputs.state.value}** was a net
**{trade_summary[0].direction}** of
**{trade_summary[0].net_interstate_abs}** MWh across state lines.
International trade totaled **{trade_summary[0].intl_imports}** MWh of
imports and **{trade_summary[0].intl_exports}** MWh of exports.
````

- [ ] **Step 2: Verify**

Refresh. Confirm a four-series line chart and narrative with a direction word and three numbers.

- [ ] **Step 3: Commit**

```bash
git add evidence/pages/electricity/state-monthly-balance.md
git commit -m "add supply and trade section"
```

---

## Task 12: Consumption by sector (section 5)

**Files:**
- Modify: `evidence/pages/electricity/state-monthly-balance.md`

- [ ] **Step 1: Append the section**

Add to the end of the file:

````markdown

## Consumption by sector

Retail sales broken out by customer class. Residential and commercial
demand swap the top spot seasonally; industrial demand is typically flatter
year-round.

```sql consumption
select
  period,
  consumption_residential_mwh    as residential,
  consumption_commercial_mwh     as commercial,
  consumption_industrial_mwh     as industrial,
  consumption_transportation_mwh as transportation,
  consumption_other_mwh          as other
from electricity.state_monthly_balance
where state = '${inputs.state.value}'
  and period between '${inputs.range.start}' and '${inputs.range.end}'
order by period
```

<AreaChart
  data={consumption}
  x=period
  y={["residential","commercial","industrial","transportation","other"]}
  type=stacked
  yFmt="#,##0"
  title="Retail consumption by sector"
/>

```sql consumption_summary
with latest as (
  select *
  from electricity.state_monthly_balance
  where state = '${inputs.state.value}'
  order by period desc
  limit 1
),
top_sector as (
  select sector, amt
  from (
    select 'residential'    as sector, consumption_residential_mwh    as amt from latest
    union all select 'commercial',     consumption_commercial_mwh     from latest
    union all select 'industrial',     consumption_industrial_mwh     from latest
    union all select 'transportation', consumption_transportation_mwh from latest
    union all select 'other',          consumption_other_mwh          from latest
  ) s
  order by amt desc nulls last
  limit 1
)
select
  latest.consumption_total_mwh as total_mwh,
  top_sector.sector             as top_sector,
  round(100.0 * top_sector.amt / nullif(latest.consumption_total_mwh, 0), 1) as top_sector_share
from latest, top_sector
```

Of the **{consumption_summary[0].total_mwh}** MWh consumed in the most
recent month, the largest sector was **{consumption_summary[0].top_sector}**
at **{consumption_summary[0].top_sector_share}%** of the total.
````

- [ ] **Step 2: Verify**

Refresh. Confirm a five-series stacked area chart and narrative with a sector name and share.

- [ ] **Step 3: Commit**

```bash
git add evidence/pages/electricity/state-monthly-balance.md
git commit -m "add consumption by sector section"
```

---

## Task 13: Balance check (section 6)

**Files:**
- Modify: `evidence/pages/electricity/state-monthly-balance.md`

- [ ] **Step 1: Append the section**

Add to the end of the file:

````markdown

## Balance check

A sanity check on the underlying EIA data. Supply side is generation plus
net imports; demand side is retail consumption plus estimated losses. They
should roughly match.

```sql balance
select
  period,
  (gen_total_mwh
    + coalesce(net_interstate_trade_mwh, 0)
    + coalesce(international_imports_mwh, 0)
    - coalesce(international_exports_mwh, 0)) as supply_side,
  (coalesce(consumption_total_mwh, 0)
    + coalesce(estimated_losses_mwh, 0))       as demand_side
from electricity.state_monthly_balance
where state = '${inputs.state.value}'
  and period between '${inputs.range.start}' and '${inputs.range.end}'
order by period
```

<LineChart
  data={balance}
  x=period
  y={["supply_side","demand_side"]}
  yFmt="#,##0"
  title="Supply vs demand side (MWh)"
/>

```sql balance_summary
select
  round(
    avg(
      100.0 * abs(supply_side - demand_side) / nullif((supply_side + demand_side) / 2.0, 0)
    ),
    2
  ) as residual_pct
from (
  select
    (gen_total_mwh
      + coalesce(net_interstate_trade_mwh, 0)
      + coalesce(international_imports_mwh, 0)
      - coalesce(international_exports_mwh, 0)) as supply_side,
    (coalesce(consumption_total_mwh, 0)
      + coalesce(estimated_losses_mwh, 0))       as demand_side
  from electricity.state_monthly_balance
  where state = '${inputs.state.value}'
    and period between '${inputs.range.start}' and '${inputs.range.end}'
) b
```

Supply and demand match to within **{balance_summary[0].residual_pct}%** on
average across the selected date range. Residuals come from rounding,
reporting lag, and consumption categories not captured in retail sales
(e.g. behind-the-meter generation for own-use).
````

- [ ] **Step 2: Verify**

Refresh. Confirm a two-series line chart and a narrative with a percentage.

- [ ] **Step 3: Commit**

```bash
git add evidence/pages/electricity/state-monthly-balance.md
git commit -m "add balance check section"
```

---

## Task 14: Recent months data table (section 7)

**Files:**
- Modify: `evidence/pages/electricity/state-monthly-balance.md`

- [ ] **Step 1: Append the section**

Add to the end of the file:

````markdown

## Recent months

The last 24 months of data for the selected state. Click a column header
to sort; use the search box to filter.

```sql recent
select
  period,
  gen_total_mwh         as gen,
  gen_fossil_mwh        as fossil,
  gen_renewable_mwh     as renewable,
  gen_nuclear_mwh       as nuclear,
  net_interstate_trade_mwh as net_trade,
  consumption_total_mwh    as consumption,
  estimated_losses_mwh     as losses
from electricity.state_monthly_balance
where state = '${inputs.state.value}'
order by period desc
limit 24
```

<DataTable data={recent} search=true sort=true/>
````

- [ ] **Step 2: Verify**

Refresh. Confirm a table with eight columns and a search box. Sort and filter should work.

- [ ] **Step 3: Commit**

```bash
git add evidence/pages/electricity/state-monthly-balance.md
git commit -m "add recent months data table section"
```

---

## Task 15: Write `docs/evidence.md`

**Files:**
- Create: `docs/evidence.md`

- [ ] **Step 1: Create the file**

Write `docs/evidence.md`:

````markdown
# Building Evidence Reports

[Evidence.dev](https://docs.evidence.dev/) is a framework for turning
markdown files with embedded SQL into interactive data reports. Each page
is a normal `.md` file with fenced SQL blocks and chart components —
authors write prose, the framework fills in live numbers from the
database.

Evidence complements Superset:

| Tool | Best for | Strength |
|------|----------|----------|
| Superset | Ad-hoc exploration, cross-filtering, building up a view of unfamiliar data | Rich UI, drag-and-drop charts, flexible filters |
| Evidence | Narrative reports, explaining a dataset, sharing a curated view | Chart + prose + live numbers in one document, trivially shareable as a static site |

Use Superset when you want to explore. Use Evidence when you have something
to say.

## Running it

```bash
make up                        # full stack, Evidence at http://localhost:3000
# or just Evidence:
make evidence
```

The dev server watches `evidence/pages/` — edit a page, save, the browser
updates in a couple of seconds. No restart needed.

## Anatomy of a page

Pages live in `evidence/pages/`. The path becomes the URL:
`evidence/pages/electricity/state-monthly-balance.md` →
`/electricity/state-monthly-balance`.

Open `evidence/pages/electricity/state-monthly-balance.md` alongside this
doc. The important pieces:

**Frontmatter.** YAML at the top gives the page a title:

```markdown
---
title: State Monthly Electricity Balance
---
```

**Inputs.** Components like `<Dropdown>` and `<DateRange>` create reactive
filter controls. Their values are available everywhere on the page via
`inputs.<name>.value`:

```markdown
<Dropdown name=state data={states} value=state defaultValue="CA"/>
<DateRange name=range defaultValue="Last 5 Years"/>
```

**SQL queries.** Fenced SQL blocks with a name become named data sources.
They run against the configured `transform_db` Postgres source. Inject
input values with `${inputs.x.value}`:

````markdown
```sql latest
select *
from electricity.state_monthly_balance
where state = '${inputs.state.value}'
order by period desc
limit 1
```
````

**Templated prose.** Query results are JavaScript-accessible. Interpolate
scalar values into text with `{query_name[0].column_name}`:

```markdown
In **{inputs.state.value}**, the state generated
**{latest[0].gen_total_mwh}** MWh most recently.
```

**Charts.** Components take a named query as `data` and pick the
columns to plot:

```markdown
<AreaChart data={gen_mix} x=period y={["coal","natural_gas"]} type=stacked/>
```

**Tables.** `<DataTable>` renders a sortable, searchable grid:

```markdown
<DataTable data={recent} search=true sort=true/>
```

Everything on the page re-runs when any input changes. If you change the
state dropdown, all queries that reference `${inputs.state.value}`
re-execute and every chart and every templated number updates.

## Adding a new report

1. Pick a URL. `evidence/pages/<dir>/<slug>.md` becomes `/<dir>/<slug>`.
2. Copy `state-monthly-balance.md` as a starting template.
3. Change the frontmatter `title`.
4. Rewrite the SQL queries to target your table. Keep the `${inputs.x}`
   templating if you want reactive filters.
5. Adjust the chart `y={["col1","col2"]}` arrays to match your columns.
6. Rewrite the narrative prose; update `{query_name[0].column}` references
   to match your query names.
7. Save. The page is live at its URL immediately.
8. Add it to the landing page: edit `evidence/pages/index.md` and add a
   bullet under "Reports".

## Sharing a report

Evidence builds the whole site as static HTML/JS — no server required to
view it.

```bash
make evidence-build              # produces evidence/build/
```

Then publish to a destination:

```bash
# Local directory (hand off, zip, upload, whatever)
make evidence-publish DEST=/tmp/energy-share

# S3 (requires the aws CLI and credentials)
make evidence-publish DEST=s3://my-bucket/reports/
```

Default `DEST` is `exports/evidence-build/` (project-local).

The published bundle is a full SPA — sharing means handing over the
directory, zipping it, or pointing any static host at it. There's no
per-page export; the SPA includes every page under `evidence/pages/`.

## Filters and reactive values

- `<Dropdown>` with `name=foo` exposes `inputs.foo.value`.
- `<DateRange>` with `name=foo` exposes `inputs.foo.start` and
  `inputs.foo.end`.
- In SQL: use `${inputs.foo.value}` — Evidence templates it before the
  query runs.
- In markdown: use `{inputs.foo.value}` — no `$`.
- In query result references: `{query_name[0].column_name}`.

## Troubleshooting

**Query error shown in the UI.** Click the error banner to expand the
SQL and Postgres message. Most often: column name typos, unquoted
`${inputs.foo.value}` in a string context, or a missing table.

**"Cannot read property X of undefined" in the narrative.** A
`{query_name[0].column}` reference ran before the query had rows. Add a
`limit 1` to the query, or guard with `{#if query_name.length}`.

**Numbers show as `undefined`.** The table is empty for the current
filter. Verify with `docker compose exec postgres psql -U energy -d
transform -c "select count(*) from electricity.state_monthly_balance
where state = 'CA'"`. If zero, run `make transform DOMAIN=electricity`.

**Hot reload isn't reloading.** Check
`docker compose logs evidence --tail 50` for file-watcher warnings. On
macOS with a slow filesystem, restart the container: `docker compose
restart evidence`.

**Connection refused to Postgres.** The compose service depends on
`postgres` being healthy, but if you started Evidence alone via
`docker run` or without the Compose network, it can't resolve the `postgres`
host. Use `make evidence` which goes through Compose.

**`npm ci` takes forever on build.** First build downloads the full
Evidence dependency tree — budget 1–2 minutes. Subsequent builds reuse
the layer cache.

## Under the hood

- Evidence dev server: Node 20 in the `evidence` container, port 3000.
- Source plugin: `@evidence-dev/postgres`, configured in
  `evidence/sources/transform_db/connection.yaml`, pulling env vars
  (`$POSTGRES_HOST`, `$POSTGRES_USER`, etc.) from the Compose service env.
- Dockerfile bakes `npm ci` at build time. The compose service mounts
  `./evidence:/app` for hot reload and uses a named volume
  (`evidence_node_modules`) to keep the baked `node_modules` from being
  shadowed by the host mount. This is the standard Node-in-Docker pattern.
- `evidence/build/`, `evidence/node_modules/`, and `evidence/.evidence/`
  are gitignored. Pages, sources, and config are checked in.
````

- [ ] **Step 2: Verify no broken syntax**

```bash
head -n 10 docs/evidence.md
```

Expected: the title and the first paragraph.

- [ ] **Step 3: Commit**

```bash
git add docs/evidence.md
git commit -m "write Evidence how-to guide"
```

---

## Task 16: Cross-reference doc updates

**Files:**
- Modify: `docs/README.md`
- Modify: `README.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add Evidence to `docs/README.md`**

In `docs/README.md`, find the guides table:

```markdown
| [Building Dashboards](dashboards.md) | Creating Superset dashboards, using saved queries, version control, and the interactive visualize workflow |
```

Insert a new row immediately below it:

```markdown
| [Evidence Reports](evidence.md) | Writing narrative data reports in markdown with embedded SQL, sharing the built static site |
```

- [ ] **Step 2: Update the top-level `README.md`**

In `README.md`, locate the passage that introduces Superset (search for `Superset`). Add a companion sentence that introduces Evidence. Example context — adjust to match what's actually there:

Find:
```markdown
- **Superset** — BI dashboards for interactive exploration
```

Add below it:
```markdown
- **Evidence** — narrative markdown reports with embedded SQL and charts (http://localhost:3000). See `docs/evidence.md`.
```

If `README.md` has a services table like CLAUDE.md, add an `evidence | 3000 | narrative data docs` row there too.

- [ ] **Step 3: Update `CLAUDE.md`**

In `CLAUDE.md`, locate the Services table at the bottom:

```markdown
| superset | 8088 | Apache Superset BI dashboard |
```

Append a new row:

```markdown
| evidence | 3000 | Evidence.dev narrative data docs |
```

Also add a short subsection under the dashboards guidance (or appended after the Services table), to help future Claude sessions find the doc:

```markdown
### Evidence reports

Evidence.dev runs as a Docker service on port 3000. Pages are hand-authored
markdown with embedded SQL in `evidence/pages/`. See `docs/evidence.md`
for the workflow and `docs/superpowers/specs/2026-04-16-evidence-docs-design.md`
for the design intent.
```

- [ ] **Step 4: Verify the edits rendered**

```bash
grep -c "Evidence" docs/README.md
grep -c "evidence" CLAUDE.md
grep -c "evidence" README.md
```

Expected: each count is ≥ 1 (higher is fine).

- [ ] **Step 5: Commit**

```bash
git add docs/README.md README.md CLAUDE.md
git commit -m "cross-reference Evidence from top-level docs"
```

---

## Task 17: End-to-end verification

Run the full verification checklist from the spec. No commits unless a step fails and requires a fix — in which case, open a new task, fix, and commit.

- [ ] **Step 1: Fresh stack boot**

```bash
docker compose down
make up
sleep 45
docker compose ps
```

Expected: all services listed including `evidence`. Evidence may be in `starting` state for up to 30s after the rest of the stack is healthy.

- [ ] **Step 2: Landing page loads**

```bash
curl -sf http://localhost:3000 | grep -o "State Monthly Electricity Balance"
```

Expected: the string prints.

- [ ] **Step 3: Report renders with data**

Open `http://localhost:3000/electricity/state-monthly-balance` in a browser. Check:
- Default state `CA` selected; every chart and every templated number has a value (not `undefined`, not blank).
- Change state dropdown to `TX`. Within ~2s every chart and every number in the narrative updates. No error banners.
- Change the date range. Charts re-scale; narrative percentages update.

- [ ] **Step 4: Hot reload works**

Edit `evidence/pages/electricity/state-monthly-balance.md` — change the intro text. Save. Browser refreshes within ~3s showing the new text.

Revert the edit if you want to keep the repo clean: `git checkout evidence/pages/electricity/state-monthly-balance.md`.

- [ ] **Step 5: Static build succeeds**

```bash
make evidence-build
ls evidence/build/index.html
ls evidence/build/electricity/state-monthly-balance/
```

Expected: files exist under `evidence/build/`.

- [ ] **Step 6: Publish to a local directory**

```bash
rm -rf /tmp/energy-share
make evidence-publish DEST=/tmp/energy-share
ls /tmp/energy-share/index.html
open /tmp/energy-share/index.html   # macOS; on Linux use xdg-open
```

Expected: the static site renders from the local directory.

- [ ] **Step 7: Publish to S3 (optional)**

Only if AWS credentials are configured and you have a test bucket:

```bash
make evidence-publish DEST=s3://your-bucket/energy-usa-test/
aws s3 ls s3://your-bucket/energy-usa-test/ | head
```

Expected: the build artifacts show up under that prefix.

- [ ] **Step 8: Make sure you're committed**

```bash
git status
```

Expected: no uncommitted files from Tasks 1–16. (Build output and the tmp publish target are gitignored.)

- [ ] **Step 9: Bring the stack down**

```bash
make down
```

---

## Self-Review

**Spec coverage:**

- Goal 1 (Evidence as a first-class Docker service) → Task 3 (Dockerfile) + Task 4 (compose) + Task 5 (Makefile dev targets).
- Goal 2 (hand-authored markdown workflow) → Task 1 (scaffold) + Task 15 (docs/evidence.md).
- Goal 3 (polished example report) → Tasks 8–14.
- Goal 4 (documentation for both audiences) → Task 15 + Task 16.
- Goal 5 (shareable bundle) → Task 6 (evidence-publish) + Task 5 (evidence-build) + Task 15 (sharing section).
- Architecture / Postgres source → Task 2.
- Docker & compose → Tasks 3, 4.
- Makefile targets → Tasks 5, 6.
- Example report sections 1–7 → Tasks 8, 9, 10, 11, 12, 13, 14.
- `docs/evidence.md` sections 1–8 → Task 15.
- Cross-ref updates → Task 16.
- Verification checklist items 1–8 → Task 17.
- Risks (first-boot time, version pinning, node volume collision, deployment host, `aws` CLI dependency) → addressed in implementation via `npm ci`, package-lock commit, named volume, non-goal documentation, and clean-error s3 branch respectively.

No spec requirement is missing a task.

**Placeholder scan:** no TBDs, no "add appropriate error handling", every code step shows complete code, every verification step shows a concrete command and expected output.

**Type / name consistency:**
- Query names (`states`, `latest`, `gen_mix`, `gen_mix_summary`, `gen_rollup`, `rollup_summary`, `supply_trade`, `trade_summary`, `consumption`, `consumption_summary`, `balance`, `balance_summary`, `recent`) are each defined once before use.
- Input names (`state`, `range`) are consistent across all SQL templates.
- Column aliases used in chart `y={[...]}` arrays match the column aliases in the matching SQL block.
- Makefile target names (`evidence`, `evidence-build`, `evidence-publish`, `evidence-logs`) are consistent between `.PHONY`, the target definitions, the Makefile help strings, and `docs/evidence.md`.
- Compose service name `evidence` and named volume `evidence_node_modules` are consistent across the compose file, Dockerfile references, and docs.