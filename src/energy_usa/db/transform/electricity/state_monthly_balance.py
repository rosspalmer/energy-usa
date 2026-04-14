"""Transform functions for the electricity.state_monthly_balance table.

Reads from three ingest tables and joins them into a wide state × month view:

* ``eia.electric_power_operational`` — generation pivoted by fuel type
* ``eia.state_source_disposition`` — supply, trade, and disposition totals
* ``eia.retail_sales`` — consumption pivoted by retail sector

The query uses CTEs for the generation and consumption pivots, then LEFT JOINs
them onto ``state_source_disposition`` (the anchor, one row per state + month).
"""

from typing import Any

import psycopg

_QUERY_SQL = """
WITH generation AS (
    SELECT
        stateid,
        period,
        SUM(CASE WHEN fueltypeid = 'COW' THEN generation END) AS gen_coal_mwh,
        SUM(CASE WHEN fueltypeid = 'NG'  THEN generation END) AS gen_natural_gas_mwh,
        SUM(CASE WHEN fueltypeid = 'NUC' THEN generation END) AS gen_nuclear_mwh,
        SUM(CASE WHEN fueltypeid = 'HYC' THEN generation END) AS gen_hydro_mwh,
        SUM(CASE WHEN fueltypeid = 'SUN' THEN generation END) AS gen_solar_mwh,
        SUM(CASE WHEN fueltypeid = 'WND' THEN generation END) AS gen_wind_mwh,
        SUM(CASE WHEN fueltypeid = 'GEO' THEN generation END) AS gen_geothermal_mwh,
        SUM(CASE WHEN fueltypeid = 'BIO' THEN generation END) AS gen_biomass_mwh,
        SUM(CASE WHEN fueltypeid IN ('PEL', 'PC') THEN generation END) AS gen_petroleum_mwh
    FROM eia.electric_power_operational
    WHERE sectorid = '99'
      AND fueltypeid IN ('COW', 'NG', 'NUC', 'HYC', 'SUN', 'WND', 'GEO', 'BIO', 'PEL', 'PC')
    GROUP BY stateid, period
),
consumption AS (
    SELECT
        stateid,
        period,
        SUM(CASE WHEN sectorid = 'RES' THEN sales END) AS consumption_residential_mwh,
        SUM(CASE WHEN sectorid = 'COM' THEN sales END) AS consumption_commercial_mwh,
        SUM(CASE WHEN sectorid = 'IND' THEN sales END) AS consumption_industrial_mwh,
        SUM(CASE WHEN sectorid = 'TRA' THEN sales END) AS consumption_transportation_mwh,
        SUM(CASE WHEN sectorid = 'OTH' THEN sales END) AS consumption_other_mwh,
        SUM(CASE WHEN sectorid = 'ALL' THEN sales END) AS consumption_total_mwh
    FROM eia.retail_sales
    WHERE stateid != 'US'
    GROUP BY stateid, period
)
SELECT
    ssd.stateid AS state,
    ssd.period,
    -- Granular generation
    g.gen_coal_mwh,
    g.gen_natural_gas_mwh,
    g.gen_nuclear_mwh,
    g.gen_hydro_mwh,
    g.gen_solar_mwh,
    g.gen_wind_mwh,
    g.gen_geothermal_mwh,
    g.gen_biomass_mwh,
    g.gen_petroleum_mwh,
    -- Fossil rollup: coal + ng + petroleum
    COALESCE(g.gen_coal_mwh, 0)
        + COALESCE(g.gen_natural_gas_mwh, 0)
        + COALESCE(g.gen_petroleum_mwh, 0) AS gen_fossil_mwh,
    -- Renewable rollup: hydro + solar + wind + geo + biomass
    COALESCE(g.gen_hydro_mwh, 0)
        + COALESCE(g.gen_solar_mwh, 0)
        + COALESCE(g.gen_wind_mwh, 0)
        + COALESCE(g.gen_geothermal_mwh, 0)
        + COALESCE(g.gen_biomass_mwh, 0) AS gen_renewable_mwh,
    -- Authoritative total from EIA (not sum of fuel pivots)
    ssd.total_net_generation AS gen_total_mwh,
    -- Other = total - fossil - nuclear - renewable (catches residual)
    COALESCE(ssd.total_net_generation, 0)
        - (COALESCE(g.gen_coal_mwh, 0) + COALESCE(g.gen_natural_gas_mwh, 0) + COALESCE(g.gen_petroleum_mwh, 0))
        - COALESCE(g.gen_nuclear_mwh, 0)
        - (COALESCE(g.gen_hydro_mwh, 0) + COALESCE(g.gen_solar_mwh, 0) + COALESCE(g.gen_wind_mwh, 0)
           + COALESCE(g.gen_geothermal_mwh, 0) + COALESCE(g.gen_biomass_mwh, 0))
        AS gen_other_mwh,
    -- Trade
    ssd.total_international_imports AS international_imports_mwh,
    ssd.total_international_exports AS international_exports_mwh,
    ssd.net_interstate_trade AS net_interstate_trade_mwh,
    ssd.total_supply AS total_supply_mwh,
    -- Consumption
    c.consumption_residential_mwh,
    c.consumption_commercial_mwh,
    c.consumption_industrial_mwh,
    c.consumption_transportation_mwh,
    c.consumption_other_mwh,
    c.consumption_total_mwh,
    -- Losses
    ssd.estimated_losses AS estimated_losses_mwh
FROM eia.state_source_disposition ssd
LEFT JOIN generation g ON g.stateid = ssd.stateid AND g.period = ssd.period
LEFT JOIN consumption c ON c.stateid = ssd.stateid AND c.period = ssd.period
WHERE ssd.stateid != 'US'
ORDER BY ssd.stateid, ssd.period
"""

_UPSERT_SQL = """
INSERT INTO electricity.state_monthly_balance (
    state, period,
    gen_coal_mwh, gen_natural_gas_mwh, gen_nuclear_mwh,
    gen_hydro_mwh, gen_solar_mwh, gen_wind_mwh,
    gen_geothermal_mwh, gen_biomass_mwh, gen_petroleum_mwh,
    gen_fossil_mwh, gen_renewable_mwh, gen_other_mwh, gen_total_mwh,
    international_imports_mwh, international_exports_mwh,
    net_interstate_trade_mwh, total_supply_mwh,
    consumption_residential_mwh, consumption_commercial_mwh,
    consumption_industrial_mwh, consumption_transportation_mwh,
    consumption_other_mwh, consumption_total_mwh,
    estimated_losses_mwh
)
VALUES (
    %(state)s, %(period)s,
    %(gen_coal_mwh)s, %(gen_natural_gas_mwh)s, %(gen_nuclear_mwh)s,
    %(gen_hydro_mwh)s, %(gen_solar_mwh)s, %(gen_wind_mwh)s,
    %(gen_geothermal_mwh)s, %(gen_biomass_mwh)s, %(gen_petroleum_mwh)s,
    %(gen_fossil_mwh)s, %(gen_renewable_mwh)s, %(gen_other_mwh)s, %(gen_total_mwh)s,
    %(international_imports_mwh)s, %(international_exports_mwh)s,
    %(net_interstate_trade_mwh)s, %(total_supply_mwh)s,
    %(consumption_residential_mwh)s, %(consumption_commercial_mwh)s,
    %(consumption_industrial_mwh)s, %(consumption_transportation_mwh)s,
    %(consumption_other_mwh)s, %(consumption_total_mwh)s,
    %(estimated_losses_mwh)s
)
ON CONFLICT (state, period) DO UPDATE SET
    gen_coal_mwh                   = EXCLUDED.gen_coal_mwh,
    gen_natural_gas_mwh            = EXCLUDED.gen_natural_gas_mwh,
    gen_nuclear_mwh                = EXCLUDED.gen_nuclear_mwh,
    gen_hydro_mwh                  = EXCLUDED.gen_hydro_mwh,
    gen_solar_mwh                  = EXCLUDED.gen_solar_mwh,
    gen_wind_mwh                   = EXCLUDED.gen_wind_mwh,
    gen_geothermal_mwh             = EXCLUDED.gen_geothermal_mwh,
    gen_biomass_mwh                = EXCLUDED.gen_biomass_mwh,
    gen_petroleum_mwh              = EXCLUDED.gen_petroleum_mwh,
    gen_fossil_mwh                 = EXCLUDED.gen_fossil_mwh,
    gen_renewable_mwh              = EXCLUDED.gen_renewable_mwh,
    gen_other_mwh                  = EXCLUDED.gen_other_mwh,
    gen_total_mwh                  = EXCLUDED.gen_total_mwh,
    international_imports_mwh      = EXCLUDED.international_imports_mwh,
    international_exports_mwh      = EXCLUDED.international_exports_mwh,
    net_interstate_trade_mwh       = EXCLUDED.net_interstate_trade_mwh,
    total_supply_mwh               = EXCLUDED.total_supply_mwh,
    consumption_residential_mwh    = EXCLUDED.consumption_residential_mwh,
    consumption_commercial_mwh     = EXCLUDED.consumption_commercial_mwh,
    consumption_industrial_mwh     = EXCLUDED.consumption_industrial_mwh,
    consumption_transportation_mwh = EXCLUDED.consumption_transportation_mwh,
    consumption_other_mwh          = EXCLUDED.consumption_other_mwh,
    consumption_total_mwh          = EXCLUDED.consumption_total_mwh,
    estimated_losses_mwh           = EXCLUDED.estimated_losses_mwh,
    transformed_at                 = now()
"""


def query_state_monthly_balance(conn: psycopg.Connection) -> list[dict[str, Any]]:
    """Query the state monthly electricity balance from ingest tables.

    Joins ``eia.electric_power_operational`` (generation by fuel),
    ``eia.state_source_disposition`` (trade + totals), and
    ``eia.retail_sales`` (consumption by sector) into one wide row per
    (state, month). National totals (stateid = 'US') are excluded.

    :param conn: An open psycopg connection to the **ingest** database.
    :returns: List of dicts, one per (state, period).
    """
    with conn.cursor() as cur:
        cur.execute(_QUERY_SQL)
        return cur.fetchall()


def upsert_state_monthly_balance(
    conn: psycopg.Connection, rows: list[dict[str, Any]]
) -> int:
    """Upsert state monthly balance rows into ``electricity.state_monthly_balance``.

    Idempotent via ``ON CONFLICT (state, period) DO UPDATE``.

    :param conn: An open psycopg connection to the **transform** database.
    :param rows: List of dicts as returned by :func:`query_state_monthly_balance`.
    :returns: Number of rows upserted (0 if empty).
    """
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.executemany(_UPSERT_SQL, rows)
    conn.commit()
    return len(rows)
