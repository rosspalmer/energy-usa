-- EIA electricity/rto/region-sub-ba-data: hourly load per sub-balancing authority.
-- Period stored as TEXT (EIA hourly format "YYYY-MM-DDTHH").
CREATE TABLE IF NOT EXISTS eia.rto_region_sub_ba_data (
    period TEXT NOT NULL,
    subba TEXT NOT NULL,
    subba_name TEXT,
    parent TEXT NOT NULL,
    parent_name TEXT,
    value NUMERIC,
    value_units TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, subba, parent)
);
