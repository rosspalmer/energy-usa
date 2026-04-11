"""Upsert EIA state-electricity-profiles/net-metering into eia.sep_net_metering.

Annual net metering statistics by state and sector.
Period stored as DATE (Jan 1 of year). Unique key: (period, stateid, sectorid).
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period


def upsert_sep_net_metering(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA state electricity profile net-metering rows.

    :param conn: Open psycopg connection.
    :param rows: List of dicts with EIA net-metering keys.
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO eia.sep_net_metering
        (period, stateid, state_description, sectorid, sector_description,
         customers, capacity, generation, ingested_at)
    VALUES
        (%(period)s, %(stateid)s, %(state_description)s, %(sectorid)s, %(sector_description)s,
         %(customers)s, %(capacity)s, %(generation)s, now())
    ON CONFLICT (period, stateid, sectorid)
    DO UPDATE SET
        state_description = EXCLUDED.state_description,
        sector_description = EXCLUDED.sector_description,
        customers = EXCLUDED.customers,
        capacity = EXCLUDED.capacity,
        generation = EXCLUDED.generation,
        ingested_at = now()
    """
    normalized = []
    for r in rows:
        period_date = normalize_period(r.get("period"), "yearly")
        if period_date is None:
            continue
        normalized.append({
            "period": period_date,
            "stateid": r.get("stateid") or r.get("stateId"),
            "state_description": r.get("stateDescription") or r.get("state_description"),
            "sectorid": r.get("sectorid") or r.get("sectorId"),
            "sector_description": r.get("sectorDescription") or r.get("sector_description"),
            "customers": r.get("customers"),
            "capacity": r.get("capacity") or r.get("nameplate-capacity"),
            "generation": r.get("generation"),
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
