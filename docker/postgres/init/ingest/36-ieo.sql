-- EIA IEO (International Energy Outlook): long-term global projections by region and series.
-- Period stored as DATE (Jan 1 of year); ieo_year identifies which IEO vintage.
CREATE TABLE IF NOT EXISTS ingest.eia_ieo (
    period DATE NOT NULL,
    ieo_year TEXT NOT NULL,
    region_id TEXT NOT NULL,
    region_name TEXT,
    series_id TEXT NOT NULL,
    series_description TEXT,
    value NUMERIC,
    unit TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, ieo_year, region_id, series_id)
);
