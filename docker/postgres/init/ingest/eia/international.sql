-- EIA International: annual energy production/consumption/trade by country and energy product.
-- Period stored as DATE (Jan 1 of year).
CREATE TABLE IF NOT EXISTS eia.international (
    period DATE NOT NULL,
    activity_id TEXT NOT NULL,
    activity_name TEXT,
    product_id TEXT NOT NULL,
    product_name TEXT,
    country_region_id TEXT NOT NULL,
    country_region_name TEXT,
    unit TEXT NOT NULL,
    value NUMERIC,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, activity_id, product_id, country_region_id, unit)
);

CREATE INDEX IF NOT EXISTS idx_international_country ON eia.international (country_region_id, period);
