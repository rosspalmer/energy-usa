-- EIA coal/mine-production: quarterly coal mine production by state and mine type.
-- Period stored as TEXT to preserve EIA quarterly format.
CREATE TABLE IF NOT EXISTS ingest.eia_coal_mine_production (
    period TEXT NOT NULL,
    mine_state TEXT NOT NULL,
    mine_type TEXT NOT NULL,
    coal_rank_id TEXT NOT NULL,
    coal_rank_description TEXT,
    production NUMERIC,
    production_units TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, mine_state, mine_type, coal_rank_id)
);
