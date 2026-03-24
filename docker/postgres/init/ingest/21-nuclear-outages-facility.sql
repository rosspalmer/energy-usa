-- EIA nuclear-outages/facility-nuclear-outages: daily outages per nuclear facility and unit.
-- Period stored as DATE.
CREATE TABLE IF NOT EXISTS ingest.eia_nuclear_outages_facility (
    period DATE NOT NULL,
    facility_id TEXT NOT NULL,
    facility_name TEXT,
    unit_id TEXT NOT NULL,
    unit_name TEXT,
    capacity_mw NUMERIC,
    outage_mw NUMERIC,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, facility_id, unit_id)
);
