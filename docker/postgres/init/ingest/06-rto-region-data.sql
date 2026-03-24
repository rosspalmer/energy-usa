-- EIA electricity/rto/region-data: hourly demand/generation per RTO region.
-- Period stored as TEXT (EIA hourly format "YYYY-MM-DDTHH").
CREATE TABLE IF NOT EXISTS ingest.eia_rto_region_data (
    period TEXT NOT NULL,
    respondent TEXT NOT NULL,
    respondent_name TEXT,
    type TEXT NOT NULL,
    type_name TEXT,
    value NUMERIC,
    value_units TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, respondent, type)
);
