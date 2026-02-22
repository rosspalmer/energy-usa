"""Upsert EIA electricity retail-sales rows into Postgres.

Uses the eia_retail_sales table with unique (period, stateid, sectorid).
Expects row dicts with keys: period, stateid, sectorid, revenue, sales, price, customers.
"""

from typing import Any

import psycopg
from psycopg.rows import dict_row


def get_connection(database_url: str) -> psycopg.Connection:
    """Open a sync connection to Postgres.

    :param database_url: PostgreSQL connection URL (e.g. postgresql://user:pass@host:5432/db).
    :returns: An open connection; caller must close it.
    """
    return psycopg.connect(database_url, row_factory=dict_row)


def upsert_retail_sales(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA retail-sales rows into eia_retail_sales.

    Each row must have period, stateid, sectorid; revenue, sales, price, customers
    may be missing (stored as NULL). On conflict on (period, stateid, sectorid)
    existing rows are updated. ingested_at is set to now().

    :param conn: An open psycopg connection.
    :param rows: List of dicts with keys period, stateid, sectorid, and optionally
        revenue, sales, price, customers (numeric or None).
    :returns: Number of rows affected (inserted or updated).
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO eia_retail_sales (period, stateid, sectorid, revenue, sales, price, customers, ingested_at)
    VALUES (%(period)s, %(stateid)s, %(sectorid)s, %(revenue)s, %(sales)s, %(price)s, %(customers)s, now())
    ON CONFLICT (period, stateid, sectorid)
    DO UPDATE SET
        revenue = EXCLUDED.revenue,
        sales = EXCLUDED.sales,
        price = EXCLUDED.price,
        customers = EXCLUDED.customers,
        ingested_at = now()
    """
    normalized = []
    for r in rows:
        normalized.append({
            "period": r.get("period"),
            "stateid": r.get("stateid"),
            "sectorid": r.get("sectorid"),
            "revenue": r.get("revenue"),
            "sales": r.get("sales"),
            "price": r.get("price"),
            "customers": r.get("customers"),
        })
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
