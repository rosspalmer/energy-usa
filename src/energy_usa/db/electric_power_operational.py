"""Upsert EIA electricity electric-power-operational-data rows into Postgres.

Uses the eia_electric_power_operational table with unique (period, stateid, sectorid, fueltypeid).
Expects row dicts with keys: period, stateid, sectorid, fueltypeid, generation (from EIA data[]).
"""

from typing import Any

import psycopg


def upsert_electric_power_operational(
    conn: psycopg.Connection, rows: list[dict[str, Any]]
) -> int:
    """Upsert EIA electric-power-operational rows into eia_electric_power_operational.

    Each row must have period, stateid, sectorid, fueltypeid; generation may be missing.
    On conflict on (period, stateid, sectorid, fueltypeid) existing rows are updated.
    ingested_at is set to now().

    :param conn: An open psycopg connection.
    :param rows: List of dicts with keys period, stateid, sectorid, fueltypeid, and optionally
        generation (numeric or None).
    :returns: Number of rows affected (inserted or updated).
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO eia_electric_power_operational (
        period, stateid, sectorid, fueltypeid, generation, ingested_at
    )
    VALUES (%(period)s, %(stateid)s, %(sectorid)s, %(fueltypeid)s, %(generation)s, now())
    ON CONFLICT (period, stateid, sectorid, fueltypeid)
    DO UPDATE SET
        generation = EXCLUDED.generation,
        ingested_at = now()
    """
    normalized = []
    for r in rows:
        normalized.append({
            "period": r.get("period"),
            "stateid": r.get("stateid"),
            "sectorid": r.get("sectorid"),
            "fueltypeid": r.get("fueltypeid") or r.get("typeid"),
            "generation": r.get("generation") or r.get("net-generation"),
        })
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
