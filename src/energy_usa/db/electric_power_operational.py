"""Upsert EIA electricity electric-power-operational-data rows into Postgres.

Uses the eia_electric_power_operational table with unique (period, stateid, sectorid, fueltypeid).
Expects row dicts with keys: period, stateid, sectorid, fueltypeid, generation (from EIA data[]).
Rows without a valid stateid (e.g. national "ALL" totals) are skipped; table stores state-level only.
"""

import logging
from typing import Any

import psycopg

logger = logging.getLogger(__name__)


def _get(obj: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if k in obj and obj[k] is not None:
            return obj[k]
    return None


def _get_ci(obj: dict[str, Any], *names: str) -> Any:
    """Get first non-None value by key, case-insensitive."""
    lower_map = {k.lower(): (k, v) for k, v in obj.items() if v is not None}
    for name in names:
        key = name.lower()
        if key in lower_map:
            return lower_map[key][1]
    return None


def upsert_electric_power_operational(
    conn: psycopg.Connection, rows: list[dict[str, Any]]
) -> int:
    """Upsert EIA electric-power-operational rows into eia_electric_power_operational.

    Each row must have period, stateid, sectorid, fueltypeid; generation may be missing.
    Rows with null/empty stateid or stateid "ALL" (national total) are skipped.
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
    skipped_missing_state = 0
    skipped_missing_required = 0
    for r in rows:
        if not isinstance(r, dict):
            continue
        stateid = _get(r, "stateid", "stateId", "state", "State", "STATE", "location") or _get_ci(
            r, "stateid", "stateId", "state", "location"
        )
        period = _get(r, "period", "periodId", "Period") or _get_ci(r, "period", "periodId")
        if stateid is not None:
            stateid = str(stateid).strip()
        if period is not None:
            period = str(period).strip()
        # Skip national totals (ALL) or rows missing state; table is state-level only
        if not stateid or stateid.upper() == "ALL":
            skipped_missing_state += 1
            continue
        sectorid = _get(r, "sectorid", "sectorId") or _get_ci(r, "sectorid", "sectorId")
        fueltypeid = _get(r, "fueltypeid", "fueltypeId", "typeid", "typeId") or _get_ci(
            r, "fueltypeid", "fueltypeId", "typeid"
        )
        if sectorid is not None:
            sectorid = str(sectorid).strip()
        if fueltypeid is not None:
            fueltypeid = str(fueltypeid).strip()
        if not period or sectorid is None or fueltypeid is None:
            skipped_missing_required += 1
            continue
        generation = _get(r, "generation", "net-generation") or _get_ci(
            r, "generation", "net-generation"
        )
        normalized.append({
            "period": period,
            "stateid": stateid,
            "sectorid": sectorid,
            "fueltypeid": fueltypeid,
            "generation": generation,
        })
    if not normalized and rows:
        sample = rows[0]
        logger.warning(
            "eia_electric_power_operational: all %s rows skipped (missing/invalid period, stateid, sectorid, or fueltypeid); sample keys: %s",
            len(rows),
            list(sample.keys()) if isinstance(sample, dict) else type(sample),
        )
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
