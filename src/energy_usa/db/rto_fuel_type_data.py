"""Upsert EIA electricity/rto/fuel-type-data rows into ingest.eia_rto_fuel_type_data.

Hourly generation by fuel type per RTO.
Period stored as TEXT (EIA hourly format "YYYY-MM-DDTHH").
Unique key: (period, respondent, fueltype).
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period_text


def upsert_rto_fuel_type_data(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA RTO fuel-type data rows.

    :param conn: Open psycopg connection.
    :param rows: List of dicts with EIA rto/fuel-type-data keys.
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO ingest.eia_rto_fuel_type_data
        (period, respondent, respondent_name, fueltype, type_name, value, value_units, ingested_at)
    VALUES
        (%(period)s, %(respondent)s, %(respondent_name)s, %(fueltype)s, %(type_name)s,
         %(value)s, %(value_units)s, now())
    ON CONFLICT (period, respondent, fueltype)
    DO UPDATE SET
        respondent_name = EXCLUDED.respondent_name,
        type_name = EXCLUDED.type_name,
        value = EXCLUDED.value,
        value_units = EXCLUDED.value_units,
        ingested_at = now()
    """
    normalized = []
    for r in rows:
        period = normalize_period_text(r.get("period"))
        if period is None:
            continue
        normalized.append({
            "period": period,
            "respondent": r.get("respondent"),
            "respondent_name": r.get("respondent-name") or r.get("respondent_name"),
            "fueltype": r.get("fueltype"),
            "type_name": r.get("type-name") or r.get("type_name"),
            "value": r.get("value"),
            "value_units": r.get("value-units") or r.get("value_units"),
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
