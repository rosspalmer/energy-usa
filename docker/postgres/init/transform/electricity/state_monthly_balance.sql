-- Wide table: state electricity supply, trade, and consumption by month.
-- Grain: state + month. Sources: eia.electric_power_operational,
-- eia.state_source_disposition, eia.retail_sales.
CREATE TABLE IF NOT EXISTS electricity.state_monthly_balance (
    state TEXT NOT NULL,
    period DATE NOT NULL,
    -- Generation by fuel type
    gen_coal_mwh NUMERIC,
    gen_natural_gas_mwh NUMERIC,
    gen_nuclear_mwh NUMERIC,
    gen_hydro_mwh NUMERIC,
    gen_solar_mwh NUMERIC,
    gen_wind_mwh NUMERIC,
    gen_geothermal_mwh NUMERIC,
    gen_biomass_mwh NUMERIC,
    gen_petroleum_mwh NUMERIC,
    -- Rollups
    gen_fossil_mwh NUMERIC,
    gen_renewable_mwh NUMERIC,
    gen_other_mwh NUMERIC,
    gen_total_mwh NUMERIC,
    -- Trade
    international_imports_mwh NUMERIC,
    international_exports_mwh NUMERIC,
    net_interstate_trade_mwh NUMERIC,
    total_supply_mwh NUMERIC,
    -- Consumption by sector
    consumption_residential_mwh NUMERIC,
    consumption_commercial_mwh NUMERIC,
    consumption_industrial_mwh NUMERIC,
    consumption_transportation_mwh NUMERIC,
    consumption_other_mwh NUMERIC,
    consumption_total_mwh NUMERIC,
    -- Losses
    estimated_losses_mwh NUMERIC,
    transformed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (state, period)
);
