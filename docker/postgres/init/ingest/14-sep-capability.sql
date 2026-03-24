-- EIA state-electricity-profiles/capability: annual generating capability per state and fuel.
-- Period stored as DATE (Jan 1 of year).
CREATE TABLE IF NOT EXISTS ingest.eia_sep_capability (
    period DATE NOT NULL,
    stateid TEXT NOT NULL,
    state_description TEXT,
    fueltypeid TEXT NOT NULL,
    fuel_type_description TEXT,
    nameplate_capacity NUMERIC,
    net_summer_capacity NUMERIC,
    net_winter_capacity NUMERIC,
    capacity_units TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, stateid, fueltypeid)
);
