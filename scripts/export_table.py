#!/usr/bin/env python
"""Export an ingest table (or custom SQL) to CSV.

Usage:
    # Full table
    uv run python scripts/export_table.py --table eia_retail_sales --out exports/retail_sales.csv

    # With a SQL WHERE filter
    uv run python scripts/export_table.py --table eia_retail_sales --filter "stateid='CA'" --out exports/ca.csv

    # Custom SQL
    uv run python scripts/export_table.py --sql "SELECT period, stateid, sales FROM eia_retail_sales LIMIT 100" --out exports/sample.csv

Reads INGEST_DATABASE_URL from .env.
"""

import argparse
import os
import sys
from pathlib import Path


INGEST_TABLES = {
    "eia_retail_sales",
    "eia_electric_power_operational",
    "eia_state_source_disposition",
    "eia_state_summary",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a database table to CSV.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--table", choices=sorted(INGEST_TABLES), help="Table name to export.")
    group.add_argument("--sql", metavar="SQL", help="Custom SQL SELECT statement.")
    parser.add_argument("--filter", metavar="SQL_WHERE", default=None, dest="where",
                        help="Optional WHERE clause (no 'WHERE' keyword). Only used with --table.")
    parser.add_argument("--out", required=True, metavar="PATH", help="Output CSV file path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Lazy import so missing .env errors surface clearly
    from dotenv import load_dotenv
    load_dotenv()

    import pandas as pd
    from energy_usa.db.dataframe import query_to_dataframe

    db_url = os.environ.get("INGEST_DATABASE_URL")
    if not db_url:
        print("ERROR: INGEST_DATABASE_URL not set in .env or environment.")
        sys.exit(1)

    if args.sql:
        sql = args.sql
    else:
        sql = f"SELECT * FROM {args.table}"
        if args.where:
            sql += f" WHERE {args.where}"
        sql += " ORDER BY period, stateid"

    print(f"Querying: {sql[:120]}{'...' if len(sql) > 120 else ''}")

    df: pd.DataFrame = query_to_dataframe(db_url, sql)
    print(f"Rows: {len(df):,}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
