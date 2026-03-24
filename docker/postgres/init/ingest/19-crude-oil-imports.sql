-- EIA crude-oil-imports: monthly crude oil imports by origin country, grade, and destination.
-- Period stored as DATE (first of month).
CREATE TABLE IF NOT EXISTS ingest.eia_crude_oil_imports (
    period DATE NOT NULL,
    origin_id TEXT NOT NULL,
    origin_name TEXT,
    destination_id TEXT NOT NULL,
    destination_name TEXT,
    grade_id TEXT NOT NULL,
    grade_name TEXT,
    refiner_type TEXT NOT NULL,
    quantity NUMERIC,
    quantity_units TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, origin_id, destination_id, grade_id, refiner_type)
);
