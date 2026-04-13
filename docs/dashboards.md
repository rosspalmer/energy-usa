# Building Dashboards

This guide covers how to create, manage, and version-control dashboards in
Apache Superset. Dashboards are the visual layer of the data platform —
they make ingested and transformed data accessible to non-technical users.

## How It Works

Dashboards follow **Level C (interactive build)** — you describe what you
want in a visualize spec (`specs/visualize/<dashboard>.md`), then build it
in the Superset UI with Claude's guidance. This is different from ingest and
transform, which are code-generated from specs.

```
1. Write a visualize spec  →  Describe audience, questions, data, chart ideas
2. Open Superset UI        →  http://localhost:8088 (admin/admin)
3. Build charts            →  Use saved queries as starting points
4. Assemble dashboard      →  Drag charts into a layout, add filters
5. Export for version control  →  make dashboard-export
```

## Prerequisites

The full Docker stack must be running:

```bash
make up
```

Superset is at http://localhost:8088. Default login: `admin` / `admin`.

## Saved Queries — Your Starting Points

Five SQL queries are pre-seeded into Superset (under SQL Lab → Saved Queries).
Each one matches a chart in the electricity overview dashboard spec:

| Query | Database | Description |
|-------|----------|-------------|
| Retail Price by State (latest month) | Transform | Bar chart: current prices ranked |
| Price Trend by State | Transform | Line chart: monthly price over time |
| Generation vs Carbon Intensity | Transform | Scatter: generation vs emissions |
| Sales Volume by State (annual) | Transform | Map/treemap: consumption by state |
| Data Quality Summary | EIA Ingest | Table: validation pass/fail per dataset |

To use a saved query as a chart:
1. Go to **SQL Lab → Saved Queries**
2. Click a query to open it in SQL Lab
3. Run it to preview the data
4. Click **Explore** to open the chart builder
5. Choose a chart type and configure axes/filters
6. Save the chart

## Creating Your First Dashboard

Follow `specs/visualize/electricity-overview.md` as the blueprint:

1. **Create charts first** — build each chart individually from the saved queries
2. **Create a new dashboard** — Dashboards → + → name it "Electricity Overview"
3. **Add charts** — drag charts from the panel into the layout grid
4. **Add filters** — use the native filter component for state and date range
5. **Save and publish**

## Version Control

Dashboards live in the Superset database, not in code. To avoid losing work
when Docker volumes are reset:

```bash
# Export all dashboards to docker/superset/dashboards/
make dashboard-export

# Import previously exported dashboards
make dashboard-import

# List dashboards in Superset
make dashboard-list
```

Export files are ZIP archives containing YAML definitions for dashboards,
charts, datasets, and database connections. Commit them to git:

```bash
make dashboard-export
git add docker/superset/dashboards/
git commit -m "export electricity overview dashboard"
```

## Writing a Visualize Spec

Specs live in `specs/visualize/<dashboard-name>.md`. They follow a simple format:

```markdown
# Dashboard Name

## Audience
Who uses this and what decisions they make with it.

## Key questions
1. What does the dashboard answer?

## Data sources
- electricity.generation_mix
- electricity.retail_by_state

## Suggested visualizations
- Chart type: description, filterable by dimension
```

See `specs/visualize/_template.md` for the full format.

The spec is a **conversation starter** — bring it to a Claude Code session
and say "let's build this dashboard." Claude will guide you through creating
each chart and assembling the layout.

## Troubleshooting

**"No data" in charts**: Make sure you've run the transform flow first:
```bash
make transform DOMAIN=electricity
```

**Can't connect to Superset**: Verify the stack is running with `make logs SERVICE=superset`.

**Lost dashboards after volume reset**: Import from the last export:
```bash
make dashboard-import
```
