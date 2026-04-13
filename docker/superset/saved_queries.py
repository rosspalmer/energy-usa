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
