-- EIA co2-emissions/co2-emissions-aggregates: annual CO2 emissions by state, sector, and fuel.
-- Period stored as DATE (Jan 1 of year).
CREATE TABLE IF NOT EXISTS ingest.eia_co2_emissions (
    period DATE NOT NULL,
    state_id TEXT NOT NULL,
    state_description TEXT,
    sector_id TEXT NOT NULL,
    sector_description TEXT,
    fuel_id TEXT NOT NULL,
    fuel_description TEXT,
    value NUMERIC,
    value_units TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, state_id, sector_id, fuel_id)
);
