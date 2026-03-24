-- EIA STEO (Short-Term Energy Outlook): monthly short-term projections by series.
-- Period stored as DATE (first of month).
CREATE TABLE IF NOT EXISTS ingest.eia_steo (
    period DATE NOT NULL,
    series_id TEXT NOT NULL,
    series_description TEXT,
    value NUMERIC,
    unit TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, series_id)
);

CREATE INDEX IF NOT EXISTS idx_steo_series ON ingest.eia_steo (series_id);
