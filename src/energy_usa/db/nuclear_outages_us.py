"""Upsert EIA nuclear-outages/us-nuclear-outages into ingest.eia_nuclear_outages_us.

Daily US-wide nuclear capacity and outages summary.
Period stored as DATE. Unique key: (period).
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period


def upsert_nuclear_outages_us(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA US nuclear outage summary rows.

    :param conn: Open psycopg connection.
    :param rows: List of dicts with EIA us-nuclear-outages keys.
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO ingest.eia_nuclear_outages_us
        (period, capacity_mw, outage_mw, operating_mw, percent_outage, ingested_at)
    VALUES
        (%(period)s, %(capacity_mw)s, %(outage_mw)s, %(operating_mw)s, %(percent_outage)s, now())
    ON CONFLICT (period)
    DO UPDATE SET
        capacity_mw = EXCLUDED.capacity_mw,
        outage_mw = EXCLUDED.outage_mw,
        operating_mw = EXCLUDED.operating_mw,
        percent_outage = EXCLUDED.percent_outage,
        ingested_at = now()
    """
    normalized = []
    for r in rows:
        period_date = normalize_period(r.get("period"), "daily")
        if period_date is None:
            continue
        normalized.append({
            "period": period_date,
            "capacity_mw": r.get("capacity") or r.get("capacity-mw") or r.get("capacity_mw"),
            "outage_mw": r.get("outage") or r.get("outage-mw") or r.get("outage_mw"),
            "operating_mw": r.get("operating") or r.get("operating-mw") or r.get("operating_mw"),
            "percent_outage": r.get("percentOutage") or r.get("percent-outage") or r.get("percent_outage"),
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
