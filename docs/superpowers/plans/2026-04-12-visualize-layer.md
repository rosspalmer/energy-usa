# Visualize Layer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the visualize layer by writing the first dashboard spec, adding a dashboard export/import mechanism for version control, seeding useful saved queries into Superset, and documenting the interactive dashboard workflow for both audiences.

**Architecture:** The visualize layer is Level C (interactive build) — dashboard specs are conversation starters, not generation inputs. Dashboards are built in the Superset UI, but exported to JSON files in `docker/superset/dashboards/` for version control. Saved SQL queries are seeded alongside datasets so users can quickly create charts. A dashboard management script wraps the Superset REST API for export/import.

**Tech Stack:** Apache Superset (REST API), Python 3.12, Docker Compose, httpx

**Design Spec:** `docs/superpowers/specs/2026-04-10-markdown-driven-data-platform-design.md` — Visualize Spec section.

**Depends on:** Plan 1 (Superset service), Plan 4 (transform datasets registered in Superset).

---

## File Map

### Created
```
specs/visualize/electricity-overview.md            # First dashboard spec
docker/superset/saved_queries.py                   # Seed useful SQL queries on init
scripts/dashboards.py                              # Export/import dashboards via Superset API
docker/superset/dashboards/                        # Directory for exported dashboard JSON files
docs/dashboards.md                                 # Guide: building dashboards, interactive workflow
```

### Modified
```
docker/superset/init.sh                            # Run saved_queries.py after seed_databases.py
docker/superset/seed_databases.py                  # No changes needed (datasets already seeded)
Makefile                                           # Add dashboard-export, dashboard-import targets
CLAUDE.md                                          # Document dashboard commands
docs/README.md                                     # Link to dashboards guide
```

---

## Task 1: Write Electricity Overview Dashboard Spec

The first visualize spec — a conversation starter for building the electricity dashboard.

**Files:**
- Create: `specs/visualize/electricity-overview.md`

- [ ] **Step 1: Write the spec**

```markdown
# Electricity Overview Dashboard

## Audience
State energy policy analysts and industry professionals who need to compare
their state's electricity profile against regional and national benchmarks.
Should be usable by someone with no SQL or programming experience.

## Key questions this dashboard answers
1. How has my state's electricity generation mix changed over time?
2. How does my state's retail electricity price compare to neighboring states?
3. What is the relationship between generation volume and carbon intensity?
4. Which states have the highest/lowest retail electricity sales?

## Data sources
- electricity.generation_mix (transform DB) — state + month grain, has total_generation_mwh, co2_tons, carbon_intensity
- electricity.retail_by_state (transform DB) — state + month grain, has total_revenue, total_sales, avg_price, total_customers

## Suggested visualizations

### Chart 1: Retail Price by State (Bar Chart)
- **Type**: Horizontal bar chart
- **X-axis**: avg_price
- **Y-axis**: state
- **Filter**: Most recent period (auto)
- **Sort**: Descending by price
- **Purpose**: Quick comparison of current electricity prices across states

### Chart 2: Price Trend Over Time (Line Chart)
- **Type**: Multi-line time series
- **X-axis**: period
- **Y-axis**: avg_price
- **Color**: state (filtered to a selectable subset)
- **Filter**: State picker (default: top 10 by sales volume)
- **Purpose**: How has pricing changed? Spot trends and seasonal patterns

### Chart 3: Generation vs Carbon Intensity (Scatter)
- **Type**: Scatter plot
- **X-axis**: total_generation_mwh
- **Y-axis**: carbon_intensity
- **Size**: total_sales (bubble)
- **Color**: state
- **Filter**: Most recent year
- **Purpose**: Identify which high-generation states are also high-emission

### Chart 4: Sales Volume by State (Choropleth or Treemap)
- **Type**: US state map or treemap
- **Value**: total_sales
- **Filter**: Period selector
- **Purpose**: Spatial view of electricity consumption

### Chart 5: Data Quality Summary (Table)
- **Type**: Table
- **Source**: quality.audit_results (ingest DB)
- **Columns**: dataset, pass count, fail count, last_run
- **Filter**: source = 'eia'
- **Purpose**: At-a-glance data freshness and quality status

## Dashboard layout
- **Row 1**: Chart 1 (price bar, 60%) + Chart 5 (quality table, 40%)
- **Row 2**: Chart 2 (price trend, 100%)
- **Row 3**: Chart 3 (scatter, 50%) + Chart 4 (sales map, 50%)
- **Global filters**: State picker, date range

## Notes for interactive build session
- Start with the simplest chart (Chart 1) to verify data connectivity
- Use Superset's "Explore" view to iterate on each chart before adding to dashboard
- The quality table (Chart 5) uses the ingest DB connection, not transform
- For the state filter, use Superset's native dashboard filter component
```

- [ ] **Step 2: Commit**

```bash
git add specs/visualize/electricity-overview.md
git commit -m "add electricity overview dashboard spec

Level C visualize spec describing audience, key questions, five chart
types, layout, and notes for the interactive build session. Data sources:
electricity.generation_mix and electricity.retail_by_state."
```

---

## Task 2: Saved Queries Seed Script

Seed useful SQL queries into Superset so users can quickly create charts from the Explore view. These are pre-written queries that answer the dashboard's key questions.

**Files:**
- Create: `docker/superset/saved_queries.py`
- Modify: `docker/superset/init.sh`

- [ ] **Step 1: Create the saved queries script**

```python
#!/usr/bin/env python3
"""Seed saved SQL queries into Superset for quick chart creation.

Called by init.sh after seed_databases.py. Idempotent — skips queries
that already exist by label. These queries serve as starting points for
building charts in the Superset Explore view.
"""
import os

from superset import create_app
from superset.extensions import db

SAVED_QUERIES = [
    {
        "label": "Retail Price by State (latest month)",
        "database_name": "Transform",
        "schema": "electricity",
        "sql": """SELECT state, period, avg_price, total_sales, total_customers
FROM electricity.retail_by_state
WHERE period = (SELECT MAX(period) FROM electricity.retail_by_state)
ORDER BY avg_price DESC""",
        "description": "Current retail electricity price ranked by state. Use for bar chart comparisons.",
    },
    {
        "label": "Price Trend by State",
        "database_name": "Transform",
        "schema": "electricity",
        "sql": """SELECT state, period, avg_price
FROM electricity.retail_by_state
WHERE state IN ('CA', 'TX', 'NY', 'FL', 'IL', 'PA', 'OH', 'GA', 'NC', 'MI')
ORDER BY state, period""",
        "description": "Monthly price trend for the 10 largest states. Adjust the state list for your analysis.",
    },
    {
        "label": "Generation vs Carbon Intensity",
        "database_name": "Transform",
        "schema": "electricity",
        "sql": """SELECT state, period, total_generation_mwh, co2_tons, carbon_intensity
FROM electricity.generation_mix
WHERE period = (SELECT MAX(period) FROM electricity.generation_mix)
  AND total_generation_mwh > 0
ORDER BY total_generation_mwh DESC""",
        "description": "Latest generation and emission data per state. Use for scatter plot analysis.",
    },
    {
        "label": "Sales Volume by State (annual)",
        "database_name": "Transform",
        "schema": "electricity",
        "sql": """SELECT state,
       date_trunc('year', period) AS year,
       SUM(total_sales) AS annual_sales,
       SUM(total_revenue) AS annual_revenue,
       SUM(total_customers) AS annual_customers
FROM electricity.retail_by_state
GROUP BY state, date_trunc('year', period)
ORDER BY year DESC, annual_sales DESC""",
        "description": "Annual electricity sales by state. Use for map/treemap visualizations.",
    },
    {
        "label": "Data Quality Summary",
        "database_name": "EIA Ingest",
        "schema": "quality",
        "sql": """SELECT rl.dataset,
       COUNT(*) FILTER (WHERE ar.status = 'pass') AS pass_count,
       COUNT(*) FILTER (WHERE ar.status = 'fail') AS fail_count,
       COUNT(*) FILTER (WHERE ar.status = 'warn') AS warn_count,
       MAX(ar.checked_at) AS last_run
FROM quality.audit_results ar
JOIN quality.audit_rules rl ON ar.rule_id = rl.rule_id
WHERE rl.source = 'eia'
GROUP BY rl.dataset
ORDER BY rl.dataset""",
        "description": "Data quality pass/fail summary per dataset. Shows freshness of validation checks.",
    },
]

app = create_app()
with app.app_context():
    from superset.models.core import Database
    from superset.models.sql_lab import SavedQuery

    for q in SAVED_QUERIES:
        # Find the database connection
        database = db.session.query(Database).filter_by(database_name=q["database_name"]).first()
        if not database:
            print(f"  SKIP (no connection): {q['label']}")
            continue

        existing = (
            db.session.query(SavedQuery)
            .filter_by(label=q["label"], db_id=database.id)
            .first()
        )
        if not existing:
            saved = SavedQuery(
                label=q["label"],
                db_id=database.id,
                schema=q["schema"],
                sql=q["sql"],
                description=q.get("description", ""),
            )
            db.session.add(saved)
            print(f"  Added query:      {q['label']}")
        else:
            print(f"  Already exists:   {q['label']}")
    db.session.commit()

print("Saved query seeding complete.")
```

- [ ] **Step 2: Update init.sh to run saved queries**

Read `docker/superset/init.sh`. After the line that runs `seed_databases.py`, add:

```bash
echo "Seeding saved queries..."
python /app/pythonpath/saved_queries.py
```

- [ ] **Step 3: Commit**

```bash
git add docker/superset/saved_queries.py docker/superset/init.sh
git commit -m "seed saved SQL queries into Superset for quick chart creation

Five pre-written queries matching the electricity dashboard spec:
retail price by state, price trends, generation vs carbon intensity,
annual sales volume, and data quality summary. Run on init alongside
database seeding."
```

---

## Task 3: Dashboard Export/Import Script

A CLI for exporting dashboards from Superset to JSON (for version control) and importing them back.

**Files:**
- Create: `scripts/dashboards.py`
- Create: `docker/superset/dashboards/` (empty directory with .gitkeep)

- [ ] **Step 1: Create the dashboards directory**

```bash
mkdir -p docker/superset/dashboards
touch docker/superset/dashboards/.gitkeep
```

- [ ] **Step 2: Create the export/import script**

```python
#!/usr/bin/env -S uv run python
# scripts/dashboards.py
"""Export and import Superset dashboards for version control.

Usage:
    uv run python scripts/dashboards.py export
    uv run python scripts/dashboards.py import
    uv run python scripts/dashboards.py list

Dashboards are exported as ZIP files to docker/superset/dashboards/.
Requires the Superset stack to be running (make up).
"""
import argparse
import sys
from pathlib import Path

import httpx

SUPERSET_URL = "http://localhost:8088"
DASHBOARDS_DIR = Path("docker/superset/dashboards")


def _get_session() -> httpx.Client:
    """Create an authenticated Superset API session."""
    client = httpx.Client(base_url=SUPERSET_URL, timeout=30.0)
    # Login to get CSRF token and session cookie
    resp = client.post("/api/v1/security/login", json={
        "username": "admin",
        "password": "admin",
        "provider": "db",
    })
    if resp.status_code != 200:
        print(f"ERROR: Login failed ({resp.status_code}). Is Superset running?")
        sys.exit(1)
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


def cmd_list(args: argparse.Namespace) -> None:
    """List all dashboards in Superset."""
    client = _get_session()
    resp = client.get("/api/v1/dashboard/", params={"page_size": 100})
    dashboards = resp.json().get("result", [])
    if not dashboards:
        print("No dashboards found.")
        return
    print(f"{'ID':<6} {'Title':<40} {'Status':<12} Charts")
    print("-" * 70)
    for d in dashboards:
        title = d.get("dashboard_title", "Untitled")
        status = d.get("status", "draft")
        chart_count = len(d.get("charts", []))
        print(f"{d['id']:<6} {title:<40} {status:<12} {chart_count}")


def cmd_export(args: argparse.Namespace) -> None:
    """Export all dashboards to ZIP files."""
    client = _get_session()
    resp = client.get("/api/v1/dashboard/", params={"page_size": 100})
    dashboards = resp.json().get("result", [])
    if not dashboards:
        print("No dashboards to export.")
        return

    DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)
    ids = [d["id"] for d in dashboards]
    export_resp = client.get("/api/v1/dashboard/export/", params={"q": ids})
    if export_resp.status_code != 200:
        print(f"ERROR: Export failed ({export_resp.status_code})")
        sys.exit(1)

    out_path = DASHBOARDS_DIR / "dashboards_export.zip"
    out_path.write_bytes(export_resp.content)
    print(f"Exported {len(ids)} dashboard(s) to {out_path}")


def cmd_import(args: argparse.Namespace) -> None:
    """Import dashboards from a ZIP file."""
    zip_path = DASHBOARDS_DIR / "dashboards_export.zip"
    if not zip_path.exists():
        print(f"ERROR: No export file at {zip_path}")
        print("Run 'make dashboard-export' first.")
        sys.exit(1)

    client = _get_session()
    with open(zip_path, "rb") as f:
        resp = client.post(
            "/api/v1/dashboard/import/",
            files={"formData": ("dashboards_export.zip", f, "application/zip")},
            data={"overwrite": "true"},
        )
    if resp.status_code == 200:
        print(f"Imported dashboards from {zip_path}")
    else:
        print(f"ERROR: Import failed ({resp.status_code}): {resp.text[:200]}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage Superset dashboards")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="List dashboards")
    sub.add_parser("export", help="Export dashboards to docker/superset/dashboards/")
    sub.add_parser("import", help="Import dashboards from docker/superset/dashboards/")

    args = parser.parse_args()
    {"list": cmd_list, "export": cmd_export, "import": cmd_import}[args.command](args)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Commit**

```bash
git add scripts/dashboards.py docker/superset/dashboards/.gitkeep
git commit -m "add dashboard export/import script for version control

scripts/dashboards.py wraps the Superset REST API to export dashboards
as ZIP files to docker/superset/dashboards/ and import them back.
Enables version-controlling dashboard configurations."
```

---

## Task 4: Makefile Targets and Documentation

Add dashboard management commands and a comprehensive dashboards guide.

**Files:**
- Create: `docs/dashboards.md`
- Modify: `Makefile`
- Modify: `CLAUDE.md`
- Modify: `docs/README.md`

- [ ] **Step 1: Write the dashboards guide**

```markdown
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
```

- [ ] **Step 2: Add Makefile targets**

Read the current Makefile. Add after the transform section:

```makefile
# ── Dashboards ────────────────────────────────────────────────────────────────

dashboard-list:  ## List Superset dashboards
	uv run python scripts/dashboards.py list

dashboard-export:  ## Export dashboards to docker/superset/dashboards/
	uv run python scripts/dashboards.py export

dashboard-import:  ## Import dashboards from docker/superset/dashboards/
	uv run python scripts/dashboards.py import
```

Update `.PHONY` to include `dashboard-list dashboard-export dashboard-import`.

- [ ] **Step 3: Update CLAUDE.md**

Add in the Common Commands section after the transform block:

```markdown
# Dashboards (Superset management)
make dashboard-list                                # List dashboards
make dashboard-export                              # Export to docker/superset/dashboards/
make dashboard-import                              # Import from exported files
```

- [ ] **Step 4: Update docs/README.md**

Add to the Guides table:

```markdown
| [Building Dashboards](dashboards.md) | Creating Superset dashboards, using saved queries, version control, and the interactive visualize workflow |
```

- [ ] **Step 5: Commit**

```bash
git add docs/dashboards.md Makefile CLAUDE.md docs/README.md
git commit -m "add dashboards guide, Makefile targets, and documentation

docs/dashboards.md covers the full interactive workflow: saved queries,
chart creation, dashboard assembly, version control via export/import.
make dashboard-list/export/import wrap the Superset API."
```

---

## Task 5: End-to-End Verification

Verify the visualize layer is complete and all documentation is consistent.

**Files:** None — verification only.

- [ ] **Step 1: Run all tests**

```bash
uv run pytest tests/ -v --ignore=tests/integration
```

Expected: All pass (no new tests in this plan — it's docs + scripts + specs).

- [ ] **Step 2: Verify script loads**

```bash
uv run python -c "import scripts.dashboards" 2>&1 || uv run python scripts/dashboards.py --help
```

Expected: Help text printed (won't connect to Superset without the stack running).

- [ ] **Step 3: Verify specs exist**

```bash
ls specs/visualize/electricity-overview.md && echo "Spec exists"
ls docker/superset/saved_queries.py && echo "Saved queries script exists"
ls docker/superset/dashboards/.gitkeep && echo "Dashboards dir exists"
ls docs/dashboards.md && echo "Dashboards guide exists"
```

- [ ] **Step 4: Verify CLAUDE.md has all commands**

```bash
grep "dashboard-export" CLAUDE.md && echo "Dashboard commands documented"
grep "generate-ingest" CLAUDE.md && echo "Generator commands documented"
grep "validate" CLAUDE.md && echo "Validation commands documented"
grep "transform" CLAUDE.md && echo "Transform commands documented"
```

- [ ] **Step 5: Commit any fixes**

If issues found, fix and commit.
