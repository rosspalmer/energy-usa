"""Upsert EIA coal/consumption-and-quality into ingest.eia_coal_consumption_quality.

Quarterly coal consumption with heat, sulfur, and ash content by sector and rank.
Period stored as TEXT. Unique key: (period, location, sector_id, coal_rank_id).
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period_text


def upsert_coal_consumption_quality(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA coal consumption and quality rows.

    :param conn: Open psycopg connection.
    :param rows: List of dicts with EIA coal/consumption-and-quality keys.
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO ingest.eia_coal_consumption_quality
        (period, location, sector_id, coal_rank_id, coal_rank_description,
         consumption, consumption_units,
         average_heat_content, average_sulfur_content, average_ash_content, ingested_at)
    VALUES
        (%(period)s, %(location)s, %(sector_id)s, %(coal_rank_id)s, %(coal_rank_description)s,
         %(consumption)s, %(consumption_units)s,
         %(average_heat_content)s, %(average_sulfur_content)s, %(average_ash_content)s, now())
    ON CONFLICT (period, location, sector_id, coal_rank_id)
    DO UPDATE SET
        coal_rank_description = EXCLUDED.coal_rank_description,
        consumption = EXCLUDED.consumption,
        consumption_units = EXCLUDED.consumption_units,
        average_heat_content = EXCLUDED.average_heat_content,
        average_sulfur_content = EXCLUDED.average_sulfur_content,
        average_ash_content = EXCLUDED.average_ash_content,
        ingested_at = now()
    """
    normalized = []
    for r in rows:
        period = normalize_period_text(r.get("period"))
        if period is None:
            continue
        normalized.append({
            "period": period,
            "location": r.get("location") or r.get("stateId") or "US",
            "sector_id": r.get("sectorId") or r.get("sector_id") or r.get("sector") or "ALL",
            "coal_rank_id": r.get("coalRankId") or r.get("coal_rank_id") or "ALL",
            "coal_rank_description": r.get("coalRankDescription") or r.get("coal_rank_description"),
            "consumption": r.get("consumption"),
            "consumption_units": r.get("consumption-units") or "thousand short tons",
            "average_heat_content": r.get("heat-content") or r.get("average-heat-content") or r.get("averageHeatContent"),
            "average_sulfur_content": r.get("sulfur-content") or r.get("average-sulfur-content") or r.get("averageSulfurContent"),
            "average_ash_content": r.get("ash-content") or r.get("average-ash-content") or r.get("averageAshContent"),
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
