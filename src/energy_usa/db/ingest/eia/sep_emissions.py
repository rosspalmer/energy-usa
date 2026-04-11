"""Upsert EIA state-electricity-profiles/emissions-by-state-by-fuel into eia.sep_emissions.

Annual CO2, SO2, NOx emissions per state, sector, and fuel.
Period stored as DATE (Jan 1 of year). Unique key: (period, stateid, sectorid, fuel_id).
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period


def upsert_sep_emissions(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA state electricity profile emissions rows.

    :param conn: Open psycopg connection.
    :param rows: List of dicts with EIA emissions-by-state-by-fuel keys.
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO eia.sep_emissions
        (period, stateid, state_description, sectorid, sector_description,
         fuel_id, fuel_description, co2, so2, nox, value_units, ingested_at)
    VALUES
        (%(period)s, %(stateid)s, %(state_description)s, %(sectorid)s, %(sector_description)s,
         %(fuel_id)s, %(fuel_description)s, %(co2)s, %(so2)s, %(nox)s, %(value_units)s, now())
    ON CONFLICT (period, stateid, sectorid, fuel_id)
    DO UPDATE SET
        state_description = EXCLUDED.state_description,
        sector_description = EXCLUDED.sector_description,
        fuel_description = EXCLUDED.fuel_description,
        co2 = EXCLUDED.co2,
        so2 = EXCLUDED.so2,
        nox = EXCLUDED.nox,
        value_units = EXCLUDED.value_units,
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
            "sectorid": r.get("sectorid") or r.get("sectorId"),
            "sector_description": r.get("sectorDescription") or r.get("sector_description"),
            "fuel_id": r.get("fuelid") or r.get("fuelId") or r.get("fuel_id"),
            "fuel_description": r.get("fuelDescription") or r.get("fuel_description"),
            "co2": r.get("co2-thousand-metric-tons") or r.get("co2"),
            "so2": r.get("so2-short-tons") or r.get("so2"),
            "nox": r.get("nox-short-tons") or r.get("nox"),
            "value_units": r.get("co2-thousand-metric-tons-units") or r.get("co2-units") or r.get("value_units"),
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
