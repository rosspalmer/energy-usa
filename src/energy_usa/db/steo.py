"""Upsert EIA STEO (Short-Term Energy Outlook) into ingest.eia_steo.

Monthly short-term projections by series.
Period stored as DATE (first of month). Unique key: (period, series_id).
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period


def upsert_steo(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA STEO rows.

    :param conn: Open psycopg connection.
    :param rows: List of dicts with EIA STEO keys.
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO ingest.eia_steo
        (period, series_id, series_description, value, unit, ingested_at)
    VALUES
        (%(period)s, %(series_id)s, %(series_description)s, %(value)s, %(unit)s, now())
    ON CONFLICT (period, series_id)
    DO UPDATE SET
        series_description = EXCLUDED.series_description,
        value = EXCLUDED.value,
        unit = EXCLUDED.unit,
        ingested_at = now()
    """
    normalized = []
    for r in rows:
        period_date = normalize_period(r.get("period"), "monthly")
        if period_date is None:
            continue
        normalized.append({
            "period": period_date,
            "series_id": r.get("seriesId") or r.get("series_id") or r.get("series") or r.get("msn") or "NA",
            "series_description": r.get("seriesDescription") or r.get("series-description") or r.get("series_description"),
            "value": r.get("value"),
            "unit": r.get("unit") or r.get("units"),
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
