-- EIA petroleum/pri/gnd: weekly retail gasoline and diesel prices by area.
-- Period stored as DATE (the specific week date EIA returns).
CREATE TABLE IF NOT EXISTS ingest.eia_petroleum_prices (
    period DATE NOT NULL,
    duoarea TEXT NOT NULL,
    area_name TEXT,
    product TEXT NOT NULL,
    product_name TEXT,
    process TEXT NOT NULL,
    process_name TEXT,
    series TEXT NOT NULL,
    series_description TEXT,
    value NUMERIC,
    units TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, series)
);

CREATE INDEX IF NOT EXISTS idx_petroleum_prices_area ON ingest.eia_petroleum_prices (duoarea, period);
