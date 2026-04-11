-- EIA natural-gas/stor/sum: monthly natural gas storage by area.
-- Period stored as DATE (first of month).
CREATE TABLE IF NOT EXISTS eia.natural_gas_storage (
    period DATE NOT NULL,
    duoarea TEXT NOT NULL,
    area_name TEXT,
    process TEXT NOT NULL,
    process_name TEXT,
    series TEXT NOT NULL,
    series_description TEXT,
    value NUMERIC,
    units TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, series)
);
