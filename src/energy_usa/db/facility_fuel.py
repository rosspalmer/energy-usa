"""Upsert EIA electricity/facility-fuel into ingest.eia_facility_fuel.

Annual generation and fuel consumption per plant and fuel type.
Period stored as DATE (Jan 1 of year). Unique key: (period, plantid, fuel_type).
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period


def upsert_facility_fuel(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA facility-fuel rows.

    :param conn: Open psycopg connection.
    :param rows: List of dicts with EIA facility-fuel keys.
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO ingest.eia_facility_fuel
        (period, plantid, plant_name, state, state_description,
         fuel_type, fuel_type_description, prime_mover,
         generation, consumption_ej, consumption_mmbtus, ingested_at)
    VALUES
        (%(period)s, %(plantid)s, %(plant_name)s, %(state)s, %(state_description)s,
         %(fuel_type)s, %(fuel_type_description)s, %(prime_mover)s,
         %(generation)s, %(consumption_ej)s, %(consumption_mmbtus)s, now())
    ON CONFLICT (period, plantid, fuel_type)
    DO UPDATE SET
        plant_name = EXCLUDED.plant_name,
        state = EXCLUDED.state,
        state_description = EXCLUDED.state_description,
        fuel_type_description = EXCLUDED.fuel_type_description,
        prime_mover = EXCLUDED.prime_mover,
        generation = EXCLUDED.generation,
        consumption_ej = EXCLUDED.consumption_ej,
        consumption_mmbtus = EXCLUDED.consumption_mmbtus,
        ingested_at = now()
    """
    normalized = []
    for r in rows:
        period_date = normalize_period(r.get("period"), "yearly")
        if period_date is None:
            continue
        normalized.append({
            "period": period_date,
            "plantid": r.get("plantid"),
            "plant_name": r.get("plantName") or r.get("plant_name"),
            "state": r.get("state") or r.get("stateid"),
            "state_description": r.get("stateDescription") or r.get("state_description"),
            "fuel_type": r.get("fuel2002") or r.get("fuel_type") or r.get("fuelTypeId"),
            "fuel_type_description": r.get("fuelTypeDescription") or r.get("fuel_type_description"),
            "prime_mover": r.get("primeMover") or r.get("prime_mover"),
            "generation": r.get("generation"),
            "consumption_ej": None,
            "consumption_mmbtus": r.get("total-consumption-btu") or r.get("consumption-mmbtus") or r.get("consumption_mmbtus"),
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
