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
They run against DuckDB (in-browser), **not directly against Postgres**.
DuckDB can only see Postgres tables that have been materialized as parquet
by a source-level query. Two-step flow:

1. Write a source query at `evidence/sources/transform_db/queries/<name>.sql`
   that reads from the real Postgres table.
2. Reference it from the page as `transform_db.<name>`.

Source query (`evidence/sources/transform_db/queries/state_monthly_balance.sql`):

```sql
select *
from electricity.state_monthly_balance
```

Page inline query — note the `transform_db.` prefix:

````markdown
```sql latest
select *
from transform_db.state_monthly_balance
where state = '${inputs.state.value}'
order by period desc
limit 1
```
````

Inject input values with `${inputs.x.value}`. Source queries are materialized
whenever you run `npm run sources` inside the container (or restart the
service); changes to source SQL require a re-run, changes to inline page SQL
hot-reload.

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
<DataTable data={recent} search=true sort="period desc"/>
```

Column headers are click-to-sort by default; the `sort` attribute takes a
column name (not a boolean) to set the initial sort order.

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
