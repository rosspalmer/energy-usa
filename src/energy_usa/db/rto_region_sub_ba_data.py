"""Upsert EIA electricity/rto/region-sub-ba-data into ingest.eia_rto_region_sub_ba_data.

Hourly load per sub-balancing authority within an RTO.
Period stored as TEXT (EIA hourly format "YYYY-MM-DDTHH").
Unique key: (period, subba, parent).
"""

from typing import Any

import psycopg

from energy_usa.db.period import normalize_period_text, safe_numeric


def upsert_rto_region_sub_ba_data(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert EIA RTO sub-BA data rows.

    :param conn: Open psycopg connection.
    :param rows: List of dicts with EIA rto/region-sub-ba-data keys.
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO ingest.eia_rto_region_sub_ba_data
        (period, subba, subba_name, parent, parent_name, value, value_units, ingested_at)
    VALUES
        (%(period)s, %(subba)s, %(subba_name)s, %(parent)s, %(parent_name)s,
         %(value)s, %(value_units)s, now())
    ON CONFLICT (period, subba, parent)
    DO UPDATE SET
        subba_name = EXCLUDED.subba_name,
        parent_name = EXCLUDED.parent_name,
        value = EXCLUDED.value,
        value_units = EXCLUDED.value_units,
        ingested_at = now()
    """
    normalized = []
    for r in rows:
        period = normalize_period_text(r.get("period"))
        if period is None:
            continue
        normalized.append({
            "period": period,
            "subba": r.get("subba"),
            "subba_name": r.get("subba-name") or r.get("subba_name"),
            "parent": r.get("parent"),
            "parent_name": r.get("parent-name") or r.get("parent_name"),
            "value": safe_numeric(r.get("value")),
            "value_units": r.get("value-units") or r.get("value_units"),
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
