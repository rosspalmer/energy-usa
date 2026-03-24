-- EIA electricity/rto/fuel-type-data: hourly generation by fuel type per RTO.
-- Period stored as TEXT (EIA hourly format "YYYY-MM-DDTHH").
CREATE TABLE IF NOT EXISTS ingest.eia_rto_fuel_type_data (
    period TEXT NOT NULL,
    respondent TEXT NOT NULL,
    respondent_name TEXT,
    fueltype TEXT NOT NULL,
    type_name TEXT,
    value NUMERIC,
    value_units TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, respondent, fueltype)
);
