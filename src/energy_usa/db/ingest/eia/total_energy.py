"""Upsert EIA total-energy into eia.total_energy.

Monthly/annual US total energy by series (MSN codes).
Period stored as DATE. Unique key: (period, msn).
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period, safe_numeric


def upsert_total_energy(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA total energy rows.

    :param conn: Open psycopg connection.
    :param rows: List of dicts with EIA total-energy keys.
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO eia.total_energy
        (period, msn, series_description, value, unit, ingested_at)
    VALUES
        (%(period)s, %(msn)s, %(series_description)s, %(value)s, %(unit)s, now())
    ON CONFLICT (period, msn)
    DO UPDATE SET
        series_description = EXCLUDED.series_description,
        value = EXCLUDED.value,
        unit = EXCLUDED.unit,
        ingested_at = now()
    """
    normalized = []
    for r in rows:
        # Total energy can be monthly or annual; try monthly first
        period_date = normalize_period(r.get("period"), "monthly")
        if period_date is None:
            continue
        normalized.append({
            "period": period_date,
            "msn": r.get("msn") or r.get("seriesId") or r.get("series") or "NA",
            "series_description": r.get("seriesDescription") or r.get("series-description") or r.get("series_description"),
            "value": safe_numeric(r.get("value")),
            "unit": r.get("unit") or r.get("units"),
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
