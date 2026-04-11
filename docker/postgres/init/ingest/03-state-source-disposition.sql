-- Ingest table for EIA state-electricity-profiles source-disposition data.
-- Unique on (period, stateid) for idempotent upserts.
CREATE TABLE IF NOT EXISTS ingest.eia_state_source_disposition (
    period DATE NOT NULL,
    stateid TEXT NOT NULL,
    net_interstate_trade NUMERIC,
    total_disposition NUMERIC,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, stateid)
);
