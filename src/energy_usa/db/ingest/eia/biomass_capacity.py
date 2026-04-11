"""Upsert EIA densified-biomass/capacity-by-region into eia.biomass_capacity.

Annual wood pellet production capacity by region.
Period stored as DATE (Jan 1 of year). Unique key: (period, region_id).
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period


def upsert_biomass_capacity(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA densified biomass capacity rows.

    :param conn: Open psycopg connection.
    :param rows: List of dicts with EIA biomass capacity keys.
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO eia.biomass_capacity
        (period, region_id, region_name, capacity, unit, ingested_at)
    VALUES
        (%(period)s, %(region_id)s, %(region_name)s, %(capacity)s, %(unit)s, now())
    ON CONFLICT (period, region_id)
    DO UPDATE SET
        region_name = EXCLUDED.region_name,
        capacity = EXCLUDED.capacity,
        unit = EXCLUDED.unit,
        ingested_at = now()
    """
    normalized = []
    for r in rows:
        period_date = normalize_period(r.get("period"), "yearly")
        if period_date is None:
            continue
        normalized.append({
            "period": period_date,
            "region_id": r.get("regionId") or r.get("region_id") or r.get("region") or "NA",
            "region_name": r.get("regionName") or r.get("region_name"),
            "capacity": r.get("capacity"),
            "unit": r.get("unit") or r.get("units") or "thousand short tons per year",
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
