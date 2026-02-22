"""Upsert EIA state-electricity-profiles summary rows into Postgres.

Uses the eia_state_summary table with unique (period, stateid).
Expects row dicts with keys: period, stateid, and optionally average-retail-price,
total-generation, total-consumption (EIA returns hyphenated keys; we map to snake_case).
"""

from typing import Any

import psycopg


def upsert_state_summary(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA state summary rows into eia_state_summary.

    Each row must have period, stateid; data columns may be missing.
    EIA API returns hyphenated keys; we normalize to snake_case.
    On conflict on (period, stateid) existing rows are updated. ingested_at is set to now().

    :param conn: An open psycopg connection.
    :param rows: List of dicts with keys period, stateid, and optionally
        average-retail-price, total-generation, total-consumption (or snake_case equivalents).
    :returns: Number of rows affected (inserted or updated).
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO eia_state_summary (
        period, stateid, average_retail_price, total_generation, total_consumption, ingested_at
    )
    VALUES (%(period)s, %(stateid)s, %(average_retail_price)s, %(total_generation)s, %(total_consumption)s, now())
    ON CONFLICT (period, stateid)
    DO UPDATE SET
        average_retail_price = EXCLUDED.average_retail_price,
        total_generation = EXCLUDED.total_generation,
        total_consumption = EXCLUDED.total_consumption,
        ingested_at = now()
    """
    normalized = []
    for r in rows:
        normalized.append({
            "period": r.get("period"),
            "stateid": r.get("stateid") or r.get("state"),
            "average_retail_price": r.get("average-retail-price") or r.get("average_retail_price"),
            "total_generation": r.get("total-generation") or r.get("total_generation"),
            "total_consumption": r.get("total-consumption") or r.get("total_consumption"),
        })
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
