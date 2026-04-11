-- EIA natural-gas/pri/sum: monthly natural gas prices by area, process, and series.
-- Period stored as DATE (first of month).
CREATE TABLE IF NOT EXISTS eia.natural_gas_prices (
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

CREATE INDEX IF NOT EXISTS idx_ng_prices_area ON eia.natural_gas_prices (duoarea, period);
