-- EIA state-electricity-profiles/net-metering: annual net metering by state and sector.
-- Period stored as DATE (Jan 1 of year).
CREATE TABLE IF NOT EXISTS eia.sep_net_metering (
    period DATE NOT NULL,
    stateid TEXT NOT NULL,
    state_description TEXT,
    sectorid TEXT NOT NULL,
    sector_description TEXT,
    customers NUMERIC,
    capacity NUMERIC,
    generation NUMERIC,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, stateid, sectorid)
);
