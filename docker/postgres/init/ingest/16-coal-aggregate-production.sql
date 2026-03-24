-- EIA coal/aggregate-production: quarterly US coal production by rank and location.
-- Period stored as TEXT to preserve EIA quarterly format (e.g. "2024-Q2").
CREATE TABLE IF NOT EXISTS ingest.eia_coal_aggregate_production (
    period TEXT NOT NULL,
    location TEXT NOT NULL,
    coal_rank_id TEXT NOT NULL,
    coal_rank_description TEXT,
    production NUMERIC,
    production_units TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, location, coal_rank_id)
);
