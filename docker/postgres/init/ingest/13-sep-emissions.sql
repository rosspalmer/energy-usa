-- EIA state-electricity-profiles/emissions-by-state-by-fuel: annual CO2/SO2/NOx per state+fuel.
-- Period stored as DATE (Jan 1 of year).
CREATE TABLE IF NOT EXISTS ingest.eia_sep_emissions (
    period DATE NOT NULL,
    stateid TEXT NOT NULL,
    state_description TEXT,
    sectorid TEXT NOT NULL,
    sector_description TEXT,
    fuel_id TEXT NOT NULL,
    fuel_description TEXT,
    co2 NUMERIC,
    so2 NUMERIC,
    nox NUMERIC,
    value_units TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, stateid, sectorid, fuel_id)
);
