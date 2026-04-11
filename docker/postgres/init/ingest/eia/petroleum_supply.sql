-- EIA petroleum/sum/snd: monthly petroleum supply and disposition by area and product.
-- Period stored as DATE (first of month).
CREATE TABLE IF NOT EXISTS eia.petroleum_supply (
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

CREATE INDEX IF NOT EXISTS idx_petroleum_supply_area ON eia.petroleum_supply (duoarea, period);
