-- Ingest table for EIA state-electricity-profiles source-disposition data.
-- Unique on (period, stateid) for idempotent upserts.
CREATE TABLE IF NOT EXISTS eia.state_source_disposition (
    period DATE NOT NULL,
    stateid TEXT NOT NULL,
    total_net_generation NUMERIC,
    total_international_imports NUMERIC,
    total_international_exports NUMERIC,
    net_interstate_trade NUMERIC,
    total_supply NUMERIC,
    total_disposition NUMERIC,
    estimated_losses NUMERIC,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, stateid)
);
