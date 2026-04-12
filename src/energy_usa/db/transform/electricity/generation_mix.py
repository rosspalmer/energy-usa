"""Transform functions for the electricity.generation_mix table.

Reads raw generation and CO2 emissions data from the ingest DB (``eia.*``
tables) and writes aggregated, carbon-intensity-enriched rows to the transform
DB (``electricity.generation_mix``).

The carbon intensity metric (tons CO2 per MWh) gives analysts a way to
compare the emissions footprint of electricity generation across states and
over time without needing to join two raw tables themselves.
"""

from typing import Any

import psycopg

_QUERY_SQL = """
SELECT
    ssd.stateid AS state,
    ssd.period,
    SUM(ssd.generation) AS total_generation_mwh,
    co2.co2_tons,
    CASE
        WHEN SUM(ssd.generation) > 0
        THEN co2.co2_tons / SUM(ssd.generation)
        ELSE NULL
    END AS carbon_intensity
FROM eia.state_source_disposition ssd
LEFT JOIN (
    SELECT state_id, period, SUM(value) AS co2_tons
    FROM eia.co2_emissions
    WHERE fuel_id = 'TO' AND sector_id = 'EC'
    GROUP BY state_id, period
) co2 ON ssd.stateid = co2.state_id
     AND date_trunc('year', ssd.period) = co2.period
WHERE ssd.stateid != 'US'
GROUP BY ssd.stateid, ssd.period, co2.co2_tons
ORDER BY ssd.stateid, ssd.period
"""

_UPSERT_SQL = """
INSERT INTO electricity.generation_mix
    (state, period, total_generation_mwh, co2_tons, carbon_intensity)
VALUES
    (%(state)s, %(period)s, %(total_generation_mwh)s, %(co2_tons)s, %(carbon_intensity)s)
ON CONFLICT (state, period) DO UPDATE SET
    total_generation_mwh = EXCLUDED.total_generation_mwh,
    co2_tons             = EXCLUDED.co2_tons,
    carbon_intensity     = EXCLUDED.carbon_intensity
"""


def query_generation_mix(conn: psycopg.Connection) -> list[dict[str, Any]]:
    """Query aggregated generation and carbon-intensity rows from the ingest DB.

    Joins ``eia.state_source_disposition`` (monthly generation by state) with
    ``eia.co2_emissions`` (annual CO2 totals for the electric sector) to produce
    one row per (state, period) with a derived ``carbon_intensity`` field.

    National totals (``stateid = 'US'``) are excluded; only state-level rows
    are returned.

    :param conn: An open psycopg connection to the ingest database with the
        ``dict_row`` row factory (as returned by
        :func:`energy_usa.db.connection.get_connection`).
    :returns: List of dicts with keys: ``state``, ``period``,
        ``total_generation_mwh``, ``co2_tons``, ``carbon_intensity``.
    """
    with conn.cursor() as cur:
        cur.execute(_QUERY_SQL)
        return cur.fetchall()


def upsert_generation_mix(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert generation-mix rows into ``electricity.generation_mix``.

    Each row must have the keys returned by :func:`query_generation_mix`:
    ``state``, ``period``, ``total_generation_mwh``, ``co2_tons``, and
    ``carbon_intensity``. On conflict on ``(state, period)`` the numeric
    columns are overwritten with the incoming values, making the operation
    idempotent and safe to re-run.

    :param conn: An open psycopg connection to the transform database.
    :param rows: List of dicts as returned by :func:`query_generation_mix`.
    :returns: Number of rows upserted (0 if ``rows`` is empty).
    """
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.executemany(_UPSERT_SQL, rows)
    conn.commit()
    return len(rows)
