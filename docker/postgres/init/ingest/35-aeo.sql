-- EIA AEO (Annual Energy Outlook): long-term US energy projections by scenario and series.
-- Period stored as DATE (Jan 1 of year); aeo_year identifies which AEO vintage.
CREATE TABLE IF NOT EXISTS ingest.eia_aeo (
    period DATE NOT NULL,
    aeo_year TEXT NOT NULL,
    scenario TEXT NOT NULL,
    series_id TEXT NOT NULL,
    series_description TEXT,
    value NUMERIC,
    unit TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, aeo_year, scenario, series_id)
);

CREATE INDEX IF NOT EXISTS idx_aeo_series ON ingest.eia_aeo (series_id, aeo_year);
