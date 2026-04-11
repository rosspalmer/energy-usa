"""Upsert EIA electricity/rto/interchange-data into ingest.eia_rto_interchange_data.

Hourly interchange (power flows) between RTOs.
Period stored as TEXT (EIA hourly format "YYYY-MM-DDTHH").
Unique key: (period, fromba, toba).
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period_text, safe_numeric


def upsert_rto_interchange_data(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA RTO interchange data rows.

    :param conn: Open psycopg connection.
    :param rows: List of dicts with EIA rto/interchange-data keys.
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO ingest.eia_rto_interchange_data
        (period, fromba, fromba_name, toba, toba_name, value, value_units, ingested_at)
    VALUES
        (%(period)s, %(fromba)s, %(fromba_name)s, %(toba)s, %(toba_name)s,
         %(value)s, %(value_units)s, now())
    ON CONFLICT (period, fromba, toba)
    DO UPDATE SET
        fromba_name = EXCLUDED.fromba_name,
        toba_name = EXCLUDED.toba_name,
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
            "fromba": r.get("fromba"),
            "fromba_name": r.get("fromba-name") or r.get("fromba_name"),
            "toba": r.get("toba"),
            "toba_name": r.get("toba-name") or r.get("toba_name"),
            "value": safe_numeric(r.get("value")),
            "value_units": r.get("value-units") or r.get("value_units"),
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
