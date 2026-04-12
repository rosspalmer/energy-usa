-- Electricity generation by fuel type with CO2 emissions by state and period.
-- Grain: state + month. Sources: eia.state_source_disposition, eia.co2_emissions.
CREATE TABLE IF NOT EXISTS electricity.generation_mix (
    state TEXT NOT NULL,
    period DATE NOT NULL,
    total_generation_mwh NUMERIC,
    co2_tons NUMERIC,
    carbon_intensity NUMERIC,
    transformed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (state, period)
);
