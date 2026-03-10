"""Upsert EIA state-electricity-profiles source-disposition rows into Postgres.

Uses the eia_state_source_disposition table with unique (period, stateid).
Expects row dicts with keys: period, stateid, net-interstate-trade, total-disposition
(EIA returns hyphenated keys; we map to net_interstate_trade, total_disposition).
Period is stored as DATE (first day of month); cadence is monthly.
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period


def upsert_state_source_disposition(
    conn: psycopg.Connection, rows: list[dict[str, Any]]
) -> int:
    """Upsert EIA source-disposition rows into eia_state_source_disposition.

    Each row must have period, stateid; net_interstate_trade and total_disposition may be missing.
    EIA API returns keys "net-interstate-trade" and "total-disposition"; we normalize to snake_case.
    On conflict on (period, stateid) existing rows are updated. ingested_at is set to now().

    :param conn: An open psycopg connection.
    :param rows: List of dicts with keys period, stateid, and optionally net-interstate-trade,
        total-disposition (or net_interstate_trade, total_disposition).
    :returns: Number of rows affected (inserted or updated).
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO eia_state_source_disposition (
        period, stateid, net_interstate_trade, total_disposition, ingested_at
    )
    VALUES (%(period)s, %(stateid)s, %(net_interstate_trade)s, %(total_disposition)s, now())
    ON CONFLICT (period, stateid)
    DO UPDATE SET
        net_interstate_trade = EXCLUDED.net_interstate_trade,
        total_disposition = EXCLUDED.total_disposition,
        ingested_at = now()
    """
    normalized = []
    for r in rows:
        period_date = normalize_period(r.get("period"), "monthly")
        if period_date is None:
            continue
        normalized.append({
            "period": period_date,
            "stateid": r.get("stateid") or r.get("state"),
            "net_interstate_trade": r.get("net-interstate-trade") or r.get("net_interstate_trade"),
            "total_disposition": r.get("total-disposition") or r.get("total_disposition"),
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
