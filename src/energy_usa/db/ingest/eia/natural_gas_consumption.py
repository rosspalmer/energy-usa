"""Upsert EIA natural-gas/cons/sum into eia.natural_gas_consumption.

Monthly natural gas consumption by area and sector series.
Period stored as DATE (first of month). Unique key: (period, series).
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period, safe_numeric


def upsert_natural_gas_consumption(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA natural gas consumption rows.

    :param conn: Open psycopg connection.
    :param rows: List of dicts with EIA natural-gas/cons/sum keys.
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO eia.natural_gas_consumption
        (period, duoarea, area_name, process, process_name,
         series, series_description, value, units, ingested_at)
    VALUES
        (%(period)s, %(duoarea)s, %(area_name)s, %(process)s, %(process_name)s,
         %(series)s, %(series_description)s, %(value)s, %(units)s, now())
    ON CONFLICT (period, series)
    DO UPDATE SET
        duoarea = EXCLUDED.duoarea,
        area_name = EXCLUDED.area_name,
        process = EXCLUDED.process,
        process_name = EXCLUDED.process_name,
        series_description = EXCLUDED.series_description,
        value = EXCLUDED.value,
        units = EXCLUDED.units,
        ingested_at = now()
    """
    normalized = []
    for r in rows:
        period_date = normalize_period(r.get("period"), "monthly")
        if period_date is None:
            continue
        normalized.append({
            "period": period_date,
            "duoarea": r.get("duoarea") or r.get("area") or "NA",
            "area_name": r.get("area-name") or r.get("areaName") or r.get("area_name"),
            "process": r.get("process") or r.get("processId") or "NA",
            "process_name": r.get("process-name") or r.get("processName") or r.get("process_name"),
            "series": r.get("series") or r.get("seriesId") or "NA",
            "series_description": r.get("series-description") or r.get("seriesDescription") or r.get("series_description"),
            "value": safe_numeric(r.get("value")),
            "units": r.get("units") or r.get("unit"),
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
