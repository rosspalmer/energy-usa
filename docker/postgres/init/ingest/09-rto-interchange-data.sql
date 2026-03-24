-- EIA electricity/rto/interchange-data: hourly interchange between RTOs.
-- Period stored as TEXT (EIA hourly format "YYYY-MM-DDTHH").
CREATE TABLE IF NOT EXISTS ingest.eia_rto_interchange_data (
    period TEXT NOT NULL,
    fromba TEXT NOT NULL,
    fromba_name TEXT,
    toba TEXT NOT NULL,
    toba_name TEXT,
    value NUMERIC,
    value_units TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, fromba, toba)
);
