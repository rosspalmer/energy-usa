-- Ingest table for EIA electricity retail-sales data.
-- Unique on (period, stateid, sectorid) for idempotent upserts.
CREATE TABLE IF NOT EXISTS eia_retail_sales (
    period DATE NOT NULL,
    stateid TEXT NOT NULL,
    sectorid TEXT NOT NULL,
    revenue NUMERIC,
    sales NUMERIC,
    price NUMERIC,
    customers NUMERIC,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, stateid, sectorid)
);
