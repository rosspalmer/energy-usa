-- Create the ingest schema for new EIA/EPA/FERC datasets.
-- Existing public.eia_* tables are unchanged.
-- All new tables in this file and beyond go in ingest.*
CREATE SCHEMA IF NOT EXISTS ingest;
