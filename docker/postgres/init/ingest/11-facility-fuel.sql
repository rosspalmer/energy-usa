-- EIA electricity/facility-fuel: annual generation and fuel consumption per plant.
-- Period stored as DATE (Jan 1 of year).
CREATE TABLE IF NOT EXISTS ingest.eia_facility_fuel (
    period DATE NOT NULL,
    plantid TEXT NOT NULL,
    plant_name TEXT,
    state TEXT,
    state_description TEXT,
    fuel_type TEXT NOT NULL,
    fuel_type_description TEXT,
    prime_mover TEXT,
    generation NUMERIC,
    consumption_ej NUMERIC,
    consumption_mmbtus NUMERIC,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, plantid, fuel_type)
);

CREATE INDEX IF NOT EXISTS idx_eia_facility_fuel_state ON ingest.eia_facility_fuel (state, period);
