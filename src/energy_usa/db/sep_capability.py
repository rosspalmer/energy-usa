"""Upsert EIA state-electricity-profiles/capability into ingest.eia_sep_capability.

Annual generating capability per state and fuel type.
Period stored as DATE (Jan 1 of year). Unique key: (period, stateid, fueltypeid).
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period


def upsert_sep_capability(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA state electricity profile capability rows.

    :param conn: Open psycopg connection.
    :param rows: List of dicts with EIA capability keys.
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO ingest.eia_sep_capability
        (period, stateid, state_description, fueltypeid, fuel_type_description,
         nameplate_capacity, net_summer_capacity, net_winter_capacity, capacity_units, ingested_at)
    VALUES
        (%(period)s, %(stateid)s, %(state_description)s, %(fueltypeid)s, %(fuel_type_description)s,
         %(nameplate_capacity)s, %(net_summer_capacity)s, %(net_winter_capacity)s,
         %(capacity_units)s, now())
    ON CONFLICT (period, stateid, fueltypeid)
    DO UPDATE SET
        state_description = EXCLUDED.state_description,
        fuel_type_description = EXCLUDED.fuel_type_description,
        nameplate_capacity = EXCLUDED.nameplate_capacity,
        net_summer_capacity = EXCLUDED.net_summer_capacity,
        net_winter_capacity = EXCLUDED.net_winter_capacity,
        capacity_units = EXCLUDED.capacity_units,
        ingested_at = now()
    """
    normalized = []
    for r in rows:
        period_date = normalize_period(r.get("period"), "yearly")
        if period_date is None:
            continue
        normalized.append({
            "period": period_date,
            "stateid": r.get("stateid") or r.get("stateId"),
            "state_description": r.get("stateDescription") or r.get("state_description"),
            "fueltypeid": r.get("fueltypeid") or r.get("fuelTypeId") or r.get("energysourceid"),
            "fuel_type_description": r.get("fuelTypeDescription") or r.get("fuel_type_description"),
            "nameplate_capacity": r.get("nameplate-capacity-mw") or r.get("nameplatecapacity"),
            "net_summer_capacity": r.get("net-summer-capacity-mw") or r.get("summercapacity"),
            "net_winter_capacity": r.get("net-winter-capacity-mw") or r.get("wintercapacity"),
            "capacity_units": r.get("capacity-units") or "megawatts",
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
