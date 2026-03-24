"""Upsert EIA IEO (International Energy Outlook) into ingest.eia_ieo.

Long-term global energy projections by region and series.
Period stored as DATE (Jan 1 of year). ieo_year identifies the IEO vintage.
Unique key: (period, ieo_year, region_id, series_id).
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period


def upsert_ieo(conn: psycopg.Connection, rows: list[dict[str, Any]], ieo_year: str = "2023") -> int:
    """Upsert EIA IEO rows.

    :param conn: Open psycopg connection.
    :param rows: List of dicts with EIA IEO keys.
    :param ieo_year: IEO vintage year (e.g. "2023").
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO ingest.eia_ieo
        (period, ieo_year, region_id, region_name, series_id, series_description,
         value, unit, ingested_at)
    VALUES
        (%(period)s, %(ieo_year)s, %(region_id)s, %(region_name)s, %(series_id)s,
         %(series_description)s, %(value)s, %(unit)s, now())
    ON CONFLICT (period, ieo_year, region_id, series_id)
    DO UPDATE SET
        region_name = EXCLUDED.region_name,
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
            "ieo_year": ieo_year,
            "region_id": r.get("regionId") or r.get("region_id") or r.get("region") or "WORLD",
            "region_name": r.get("regionName") or r.get("region_name"),
            "series_id": r.get("seriesId") or r.get("series_id") or r.get("series") or "NA",
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
