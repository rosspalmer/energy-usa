-- EIA total-energy: monthly/annual US total energy production, consumption, and trade by series.
-- Period stored as DATE (first of month for monthly, Jan 1 for annual).
CREATE TABLE IF NOT EXISTS ingest.eia_total_energy (
    period DATE NOT NULL,
    msn TEXT NOT NULL,
    series_description TEXT,
    value NUMERIC,
    unit TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, msn)
);

CREATE INDEX IF NOT EXISTS idx_total_energy_msn ON ingest.eia_total_energy (msn);
