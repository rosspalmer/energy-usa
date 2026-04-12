"""Transform functions for the electricity.retail_by_state table.

Reads sector-level retail-sales data from the ingest DB (``eia.retail_sales``)
and aggregates it to the state level in the transform DB
(``electricity.retail_by_state``).

Aggregating across sectors (residential, commercial, industrial, …) before
writing to the transform layer keeps downstream queries simple: analysts can
compare total state-level sales, revenue, and average price without needing
to know EIA sector codes.
"""

from typing import Any

import psycopg

_QUERY_SQL = """
SELECT
    stateid AS state,
    period,
    SUM(revenue) AS total_revenue,
    SUM(sales) AS total_sales,
    CASE
        WHEN SUM(sales) > 0
        THEN SUM(revenue) / SUM(sales)
        ELSE NULL
    END AS avg_price,
    SUM(customers) AS total_customers
FROM eia.retail_sales
WHERE stateid != 'US'
GROUP BY stateid, period
ORDER BY stateid, period
"""

_UPSERT_SQL = """
INSERT INTO electricity.retail_by_state
    (state, period, total_revenue, total_sales, avg_price, total_customers)
VALUES
    (%(state)s, %(period)s, %(total_revenue)s, %(total_sales)s,
     %(avg_price)s, %(total_customers)s)
ON CONFLICT (state, period) DO UPDATE SET
    total_revenue    = EXCLUDED.total_revenue,
    total_sales      = EXCLUDED.total_sales,
    avg_price        = EXCLUDED.avg_price,
    total_customers  = EXCLUDED.total_customers
"""


def query_retail_by_state(conn: psycopg.Connection) -> list[dict[str, Any]]:
    """Query state-level retail electricity sales aggregates from the ingest DB.

    Groups ``eia.retail_sales`` by ``(stateid, period)`` across all sectors,
    computing totals for revenue, sales, and customers, and a derived average
    price (revenue ÷ sales). National totals (``stateid = 'US'``) are excluded.

    :param conn: An open psycopg connection to the ingest database with the
        ``dict_row`` row factory (as returned by
        :func:`energy_usa.db.connection.get_connection`).
    :returns: List of dicts with keys: ``state``, ``period``,
        ``total_revenue``, ``total_sales``, ``avg_price``, ``total_customers``.
    """
    with conn.cursor() as cur:
        cur.execute(_QUERY_SQL)
        return cur.fetchall()


def upsert_retail_by_state(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert retail-by-state rows into ``electricity.retail_by_state``.

    Each row must have the keys returned by :func:`query_retail_by_state`:
    ``state``, ``period``, ``total_revenue``, ``total_sales``, ``avg_price``,
    and ``total_customers``. On conflict on ``(state, period)`` the numeric
    columns are overwritten with the incoming values, making the operation
    idempotent and safe to re-run.

    :param conn: An open psycopg connection to the transform database.
    :param rows: List of dicts as returned by :func:`query_retail_by_state`.
    :returns: Number of rows upserted (0 if ``rows`` is empty).
    """
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.executemany(_UPSERT_SQL, rows)
    conn.commit()
    return len(rows)
