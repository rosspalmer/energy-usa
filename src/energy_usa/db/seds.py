"""Upsert EIA SEDS (State Energy Data System) into ingest.eia_seds.

Annual energy data by state and MSN series code.
Period stored as DATE (Jan 1 of year). Unique key: (period, msn, state_id).
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period, safe_numeric


def upsert_seds(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA SEDS rows.

    :param conn: Open psycopg connection.
    :param rows: List of dicts with EIA SEDS keys.
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO ingest.eia_seds
        (period, msn, state_id, state_description, value, unit, ingested_at)
    VALUES
        (%(period)s, %(msn)s, %(state_id)s, %(state_description)s, %(value)s, %(unit)s, now())
    ON CONFLICT (period, msn, state_id)
    DO UPDATE SET
        state_description = EXCLUDED.state_description,
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
            "msn": r.get("msn") or r.get("seriesId") or r.get("series") or "NA",
            "state_id": r.get("stateId") or r.get("state_id") or r.get("stateid") or "US",
            "state_description": r.get("stateDescription") or r.get("state_description"),
            "value": safe_numeric(r.get("value")),
            "unit": r.get("unit") or r.get("units"),
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
