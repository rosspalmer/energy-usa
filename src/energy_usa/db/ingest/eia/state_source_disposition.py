"""Upsert EIA state-electricity-profiles source-disposition rows into Postgres.

Uses the eia.state_source_disposition table with unique (period, stateid).
Expects row dicts from the EIA API with hyphenated keys (e.g.
``total-net-generation``); we normalize to snake_case for Postgres columns.
Period is stored as DATE (first day of month); cadence is monthly.
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period


def _get(row: dict, *keys: str) -> Any:
    """Return the first non-None value for the given keys."""
    for k in keys:
        v = row.get(k)
        if v is not None:
            return v
    return None


def upsert_state_source_disposition(
    conn: psycopg.Connection, rows: list[dict[str, Any]]
) -> int:
    """Upsert EIA source-disposition rows into eia.state_source_disposition.

    Each row must have period and stateid. All other columns are optional.
    EIA API returns hyphenated keys; we normalize to snake_case.
    On conflict on (period, stateid) existing rows are updated.

    :param conn: An open psycopg connection.
    :param rows: List of dicts from the EIA API.
    :returns: Number of rows affected (inserted or updated).
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO eia.state_source_disposition (
        period, stateid,
        total_net_generation, total_international_imports,
        total_international_exports, net_interstate_trade,
        total_supply, total_disposition, estimated_losses,
        ingested_at
    )
    VALUES (
        %(period)s, %(stateid)s,
        %(total_net_generation)s, %(total_international_imports)s,
        %(total_international_exports)s, %(net_interstate_trade)s,
        %(total_supply)s, %(total_disposition)s, %(estimated_losses)s,
        now()
    )
    ON CONFLICT (period, stateid)
    DO UPDATE SET
        total_net_generation       = EXCLUDED.total_net_generation,
        total_international_imports = EXCLUDED.total_international_imports,
        total_international_exports = EXCLUDED.total_international_exports,
        net_interstate_trade       = EXCLUDED.net_interstate_trade,
        total_supply               = EXCLUDED.total_supply,
        total_disposition          = EXCLUDED.total_disposition,
        estimated_losses           = EXCLUDED.estimated_losses,
        ingested_at                = now()
    """
    normalized = []
    for r in rows:
        period_date = normalize_period(r.get("period"), "monthly")
        if period_date is None:
            continue
        normalized.append({
            "period": period_date,
            "stateid": r.get("stateid") or r.get("state"),
            "total_net_generation": _get(r, "total-net-generation", "total_net_generation"),
            "total_international_imports": _get(r, "total-international-imports", "total_international_imports"),
            "total_international_exports": _get(r, "total-international-exports", "total_international_exports"),
            "net_interstate_trade": _get(r, "net-interstate-trade", "net_interstate_trade"),
            "total_supply": _get(r, "total-supply", "total_supply"),
            "total_disposition": _get(r, "total-disposition", "total_disposition"),
            "estimated_losses": _get(r, "estimated-losses", "estimated_losses"),
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
