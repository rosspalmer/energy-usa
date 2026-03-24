-- EIA coal/consumption-and-quality: quarterly coal consumption, heat, sulfur, and ash content.
-- Period stored as TEXT to preserve EIA quarterly format.
CREATE TABLE IF NOT EXISTS ingest.eia_coal_consumption_quality (
    period TEXT NOT NULL,
    location TEXT NOT NULL,
    sector_id TEXT NOT NULL,
    coal_rank_id TEXT NOT NULL,
    coal_rank_description TEXT,
    consumption NUMERIC,
    consumption_units TEXT,
    average_heat_content NUMERIC,
    average_sulfur_content NUMERIC,
    average_ash_content NUMERIC,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, location, sector_id, coal_rank_id)
);
