"""Upsert EIA co2-emissions/co2-emissions-aggregates into ingest.eia_co2_emissions.

Annual CO2 emissions by state, sector, and fuel type.
Period stored as DATE (Jan 1 of year). Unique key: (period, state_id, sector_id, fuel_id).
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period, safe_numeric


def upsert_co2_emissions(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA CO2 emissions rows.

    :param conn: Open psycopg connection.
    :param rows: List of dicts with EIA co2-emissions-aggregates keys.
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO ingest.eia_co2_emissions
        (period, state_id, state_description, sector_id, sector_description,
         fuel_id, fuel_description, value, value_units, ingested_at)
    VALUES
        (%(period)s, %(state_id)s, %(state_description)s, %(sector_id)s, %(sector_description)s,
         %(fuel_id)s, %(fuel_description)s, %(value)s, %(value_units)s, now())
    ON CONFLICT (period, state_id, sector_id, fuel_id)
    DO UPDATE SET
        state_description = EXCLUDED.state_description,
        sector_description = EXCLUDED.sector_description,
        fuel_description = EXCLUDED.fuel_description,
        value = EXCLUDED.value,
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
            "state_id": r.get("stateId") or r.get("state_id") or r.get("stateid") or "US",
            "state_description": r.get("stateDescription") or r.get("state_description"),
            "sector_id": r.get("sectorId") or r.get("sector_id") or r.get("sectorid") or "ALL",
            "sector_description": r.get("sectorDescription") or r.get("sector_description"),
            "fuel_id": r.get("fuelId") or r.get("fuel_id") or r.get("fuelid") or "ALL",
            "fuel_description": r.get("fuelDescription") or r.get("fuel_description"),
            "value": safe_numeric(r.get("value")),
            "value_units": r.get("value-units") or r.get("valueUnits") or "million metric tons CO2",
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
