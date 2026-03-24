-- EIA densified-biomass/production-by-region: annual wood pellet production by region.
-- Period stored as DATE (Jan 1 of year).
CREATE TABLE IF NOT EXISTS ingest.eia_biomass_production (
    period DATE NOT NULL,
    region_id TEXT NOT NULL,
    region_name TEXT,
    production NUMERIC,
    unit TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, region_id)
);
