"""Upsert EIA coal/mine-production into ingest.eia_coal_mine_production.

Quarterly coal production by state, mine type, and rank.
Period stored as TEXT. Unique key: (period, mine_state, mine_type, coal_rank_id).
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period_text


def upsert_coal_mine_production(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA coal mine production rows.

    :param conn: Open psycopg connection.
    :param rows: List of dicts with EIA coal/mine-production keys.
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO ingest.eia_coal_mine_production
        (period, mine_state, mine_type, coal_rank_id, coal_rank_description,
         production, production_units, ingested_at)
    VALUES
        (%(period)s, %(mine_state)s, %(mine_type)s, %(coal_rank_id)s, %(coal_rank_description)s,
         %(production)s, %(production_units)s, now())
    ON CONFLICT (period, mine_state, mine_type, coal_rank_id)
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
            "mine_state": r.get("mineState") or r.get("mine_state") or r.get("stateId") or "US",
            "mine_type": r.get("mineType") or r.get("mine_type") or r.get("mineTypeId") or "ALL",
            "coal_rank_id": r.get("coalRankId") or r.get("coal_rank_id") or "ALL",
            "coal_rank_description": r.get("coalRankDescription") or r.get("coal_rank_description"),
            "production": r.get("production"),
            "production_units": r.get("production-units") or "thousand short tons",
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
