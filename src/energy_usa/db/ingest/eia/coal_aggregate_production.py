"""Upsert EIA coal/aggregate-production into eia.coal_aggregate_production.

Quarterly US coal production by rank and location.
Period stored as TEXT (quarterly format e.g. "2024-Q2"). Unique key: (period, location, coal_rank_id).
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period_text


def upsert_coal_aggregate_production(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA coal aggregate production rows.

    :param conn: Open psycopg connection.
    :param rows: List of dicts with EIA coal/aggregate-production keys.
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO eia.coal_aggregate_production
        (period, location, coal_rank_id, coal_rank_description,
         production, production_units, ingested_at)
    VALUES
        (%(period)s, %(location)s, %(coal_rank_id)s, %(coal_rank_description)s,
         %(production)s, %(production_units)s, now())
    ON CONFLICT (period, location, coal_rank_id)
    DO UPDATE SET
        coal_rank_description = EXCLUDED.coal_rank_description,
        production = EXCLUDED.production,
        production_units = EXCLUDED.production_units,
        ingested_at = now()
    """
    normalized = []
    for r in rows:
        period = normalize_period_text(r.get("period"))
        if period is None:
            continue
        normalized.append({
            "period": period,
            "location": r.get("location") or r.get("locationId") or r.get("stateId") or "US",
            "coal_rank_id": r.get("coalRankId") or r.get("coal_rank_id") or r.get("coalrank") or "ALL",
            "coal_rank_description": r.get("coalRankDescription") or r.get("coal_rank_description"),
            "production": r.get("production"),
            "production_units": r.get("production-units") or r.get("productionUnits") or "thousand short tons",
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
