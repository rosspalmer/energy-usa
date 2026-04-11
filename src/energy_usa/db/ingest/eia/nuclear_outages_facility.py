"""Upsert EIA nuclear-outages/facility-nuclear-outages into eia.nuclear_outages_facility.

Daily nuclear outages per facility and unit.
Period stored as DATE. Unique key: (period, facility_id, unit_id).
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period


def upsert_nuclear_outages_facility(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA facility nuclear outage rows.

    :param conn: Open psycopg connection.
    :param rows: List of dicts with EIA facility-nuclear-outages keys.
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO eia.nuclear_outages_facility
        (period, facility_id, facility_name, unit_id, unit_name,
         capacity_mw, outage_mw, ingested_at)
    VALUES
        (%(period)s, %(facility_id)s, %(facility_name)s, %(unit_id)s, %(unit_name)s,
         %(capacity_mw)s, %(outage_mw)s, now())
    ON CONFLICT (period, facility_id, unit_id)
    DO UPDATE SET
        facility_name = EXCLUDED.facility_name,
        unit_name = EXCLUDED.unit_name,
        capacity_mw = EXCLUDED.capacity_mw,
        outage_mw = EXCLUDED.outage_mw,
        ingested_at = now()
    """
    normalized = []
    for r in rows:
        period_date = normalize_period(r.get("period"), "daily")
        if period_date is None:
            continue
        normalized.append({
            "period": period_date,
            "facility_id": r.get("facilityId") or r.get("facility_id") or r.get("plantId") or "UNK",
            "facility_name": r.get("facilityName") or r.get("facility_name") or r.get("plantName"),
            "unit_id": r.get("unitId") or r.get("unit_id") or r.get("generatorId") or "UNK",
            "unit_name": r.get("unitName") or r.get("unit_name"),
            "capacity_mw": r.get("capacity") or r.get("capacity-mw") or r.get("capacity_mw"),
            "outage_mw": r.get("outage") or r.get("outage-mw") or r.get("outage_mw"),
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
