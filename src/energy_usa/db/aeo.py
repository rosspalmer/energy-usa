"""Upsert EIA AEO (Annual Energy Outlook) into ingest.eia_aeo.

Long-term US energy projections by scenario and series.
Period stored as DATE (Jan 1 of year). aeo_year identifies the AEO vintage.
Unique key: (period, aeo_year, scenario, series_id).
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period


def upsert_aeo(conn: psycopg.Connection, rows: list[dict[str, Any]], aeo_year: str = "2023") -> int:
    """Upsert EIA AEO rows.

    :param conn: Open psycopg connection.
    :param rows: List of dicts with EIA AEO keys.
    :param aeo_year: AEO vintage year (e.g. "2023").
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO ingest.eia_aeo
        (period, aeo_year, scenario, series_id, series_description, value, unit, ingested_at)
    VALUES
        (%(period)s, %(aeo_year)s, %(scenario)s, %(series_id)s, %(series_description)s,
         %(value)s, %(unit)s, now())
    ON CONFLICT (period, aeo_year, scenario, series_id)
    DO UPDATE SET
        series_description = EXCLUDED.series_description,
        value = EXCLUDED.value,
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
            "aeo_year": aeo_year,
            "scenario": r.get("scenario") or r.get("scenarioId") or r.get("caseid") or "ref",
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
