"""Upsert EIA electricity/operating-generator-capacity into eia.operating_generator_capacity.

Monthly installed capacity per generator unit.
Period stored as DATE (first of month). Unique key: (period, plantid, generatorid).
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period


def upsert_operating_generator_capacity(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA operating generator capacity rows.

    :param conn: Open psycopg connection.
    :param rows: List of dicts with EIA operating-generator-capacity keys.
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO eia.operating_generator_capacity
        (period, plantid, generatorid, stateid, entity_id, entity_name,
         energy_source_code, prime_mover_code,
         nameplate_capacity_mw, net_summer_capacity_mw, net_winter_capacity_mw,
         operating_year, technology, ingested_at)
    VALUES
        (%(period)s, %(plantid)s, %(generatorid)s, %(stateid)s, %(entity_id)s, %(entity_name)s,
         %(energy_source_code)s, %(prime_mover_code)s,
         %(nameplate_capacity_mw)s, %(net_summer_capacity_mw)s, %(net_winter_capacity_mw)s,
         %(operating_year)s, %(technology)s, now())
    ON CONFLICT (period, plantid, generatorid)
    DO UPDATE SET
        stateid = EXCLUDED.stateid,
        entity_id = EXCLUDED.entity_id,
        entity_name = EXCLUDED.entity_name,
        energy_source_code = EXCLUDED.energy_source_code,
        prime_mover_code = EXCLUDED.prime_mover_code,
        nameplate_capacity_mw = EXCLUDED.nameplate_capacity_mw,
        net_summer_capacity_mw = EXCLUDED.net_summer_capacity_mw,
        net_winter_capacity_mw = EXCLUDED.net_winter_capacity_mw,
        operating_year = EXCLUDED.operating_year,
        technology = EXCLUDED.technology,
        ingested_at = now()
    """
    normalized = []
    for r in rows:
        period_date = normalize_period(r.get("period"), "monthly")
        if period_date is None:
            continue
        normalized.append({
            "period": period_date,
            "plantid": r.get("plantid"),
            "generatorid": r.get("generatorid"),
            "stateid": r.get("stateid"),
            "entity_id": r.get("entity-id") or r.get("entity_id"),
            "entity_name": r.get("entity-name") or r.get("entity_name"),
            "energy_source_code": r.get("energy-source-code") or r.get("energy_source_code"),
            "prime_mover_code": r.get("prime-mover-code") or r.get("prime_mover_code"),
            "nameplate_capacity_mw": r.get("nameplate-capacity-mw") or r.get("nameplate_capacity_mw"),
            "net_summer_capacity_mw": r.get("net-summer-capacity-mw") or r.get("net_summer_capacity_mw"),
            "net_winter_capacity_mw": r.get("net-winter-capacity-mw") or r.get("net_winter_capacity_mw"),
            "operating_year": str(r.get("operating-year") or r.get("operating_year") or ""),
            "technology": r.get("technology"),
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
