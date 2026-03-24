-- EIA electricity/rto/daily-region-data: daily demand/generation per RTO.
-- Period stored as DATE.
CREATE TABLE IF NOT EXISTS ingest.eia_rto_daily_region_data (
    period DATE NOT NULL,
    respondent TEXT NOT NULL,
    respondent_name TEXT,
    type TEXT NOT NULL,
    type_name TEXT,
    value NUMERIC,
    value_units TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, respondent, type)
);
