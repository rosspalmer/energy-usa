-- Ingest table for EIA electricity electric-power-operational-data (generation by state/sector/fuel).
-- Unique on (period, stateid, sectorid, fueltypeid) for idempotent upserts.
CREATE TABLE IF NOT EXISTS eia_electric_power_operational (
    period DATE NOT NULL,
    stateid TEXT NOT NULL,
    sectorid TEXT NOT NULL,
    fueltypeid TEXT NOT NULL,
    generation NUMERIC,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, stateid, sectorid, fueltypeid)
);
