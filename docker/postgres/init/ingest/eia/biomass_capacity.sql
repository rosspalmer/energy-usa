-- EIA densified-biomass/capacity-by-region: annual wood pellet production capacity by region.
-- Period stored as DATE (Jan 1 of year).
CREATE TABLE IF NOT EXISTS eia.biomass_capacity (
    period DATE NOT NULL,
    region_id TEXT NOT NULL,
    region_name TEXT,
    capacity NUMERIC,
    unit TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, region_id)
);
