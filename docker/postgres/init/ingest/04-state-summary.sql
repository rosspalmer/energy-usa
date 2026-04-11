-- Ingest table for EIA state-electricity-profiles summary data.
-- Unique on (period, stateid) for idempotent upserts.
CREATE TABLE IF NOT EXISTS ingest.eia_state_summary (
    period DATE NOT NULL,
    stateid TEXT NOT NULL,
    average_retail_price NUMERIC,
    total_generation NUMERIC,
    total_consumption NUMERIC,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, stateid)
);
