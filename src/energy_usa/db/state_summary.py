"""Upsert EIA state-electricity-profiles summary rows into Postgres.

Uses the eia_state_summary table with unique (period, stateid).
Expects row dicts with keys: period, stateid, and optionally average-retail-price,
total-generation, total-consumption (EIA returns hyphenated keys; we map to snake_case).
"""

import logging
from typing import Any

import psycopg

logger = logging.getLogger(__name__)


def upsert_state_summary(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA state summary rows into eia_state_summary.

    Each row must have period, stateid; data columns may be missing.
    EIA API returns hyphenated keys; we normalize to snake_case.
    On conflict on (period, stateid) existing rows are updated. ingested_at is set to now().

    :param conn: An open psycopg connection.
    :param rows: List of dicts with keys period, stateid, and optionally
        average-retail-price, total-generation, total-consumption (or snake_case equivalents).
    :returns: Number of rows affected (inserted or updated).
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO eia_state_summary (
        period, stateid, average_retail_price, total_generation, total_consumption, ingested_at
    )
    VALUES (%(period)s, %(stateid)s, %(average_retail_price)s, %(total_generation)s, %(total_consumption)s, now())
    ON CONFLICT (period, stateid)
    DO UPDATE SET
        average_retail_price = EXCLUDED.average_retail_price,
        total_generation = EXCLUDED.total_generation,
        total_consumption = EXCLUDED.total_consumption,
        ingested_at = now()
    """
    def _get(obj: dict[str, Any], *keys: str) -> Any:
        for k in keys:
            if k in obj and obj[k] is not None:
                return obj[k]
        return None

    def _get_ci(obj: dict[str, Any], *names: str) -> Any:
        """Get first non-None value by key, case-insensitive (normalize to lower)."""
        lower_map = {k.lower(): (k, v) for k, v in obj.items() if v is not None}
        for name in names:
            key = name.lower()
            if key in lower_map:
                return lower_map[key][1]
        return None

    normalized = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        # Prefer exact keys, then fall back to case-insensitive (EIA may vary casing)
        stateid = _get(r, "stateid", "stateId", "state", "State", "STATE") or _get_ci(r, "stateid", "stateId", "state")
        period = _get(r, "period", "periodId", "Period") or _get_ci(r, "period", "periodId")
        if stateid is not None:
            stateid = str(stateid).strip()
        if period is not None:
            period = str(period).strip()
        if not stateid or not period:
            continue
        normalized.append({
            "period": period,
            "stateid": stateid,
            "average_retail_price": _get(r, "average-retail-price", "average_retail_price") or _get_ci(r, "average-retail-price", "average_retail_price"),
            "total_generation": _get(r, "total-generation", "total_generation") or _get_ci(r, "total-generation", "total_generation"),
            "total_consumption": _get(r, "total-consumption", "total_consumption") or _get_ci(r, "total-consumption", "total_consumption"),
        })
    if not normalized and rows:
        sample = rows[0]
        logger.warning(
            "eia_state_summary: all %s rows skipped (missing period/stateid); sample keys: %s",
            len(rows),
            list(sample.keys()) if isinstance(sample, dict) else type(sample),
        )
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
