"""Upsert EIA electricity/rto/region-data rows into ingest.eia_rto_region_data.

Hourly demand, net generation, and total interchange per RTO region.
Period stored as TEXT (EIA hourly format "YYYY-MM-DDTHH").
Unique key: (period, respondent, type).
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period_text, safe_numeric


def upsert_rto_region_data(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA RTO region data rows.

    :param conn: Open psycopg connection.
    :param rows: List of dicts with EIA rto/region-data keys.
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO ingest.eia_rto_region_data
        (period, respondent, respondent_name, type, type_name, value, value_units, ingested_at)
    VALUES
        (%(period)s, %(respondent)s, %(respondent_name)s, %(type)s, %(type_name)s,
         %(value)s, %(value_units)s, now())
    ON CONFLICT (period, respondent, type)
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
            "type": r.get("type"),
            "type_name": r.get("type-name") or r.get("type_name"),
            "value": safe_numeric(r.get("value")),
            "value_units": r.get("value-units") or r.get("value_units"),
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
