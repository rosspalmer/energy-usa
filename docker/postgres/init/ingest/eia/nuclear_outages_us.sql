-- EIA nuclear-outages/us-nuclear-outages: daily US-wide nuclear capacity and outages.
-- Period stored as DATE.
CREATE TABLE IF NOT EXISTS eia.nuclear_outages_us (
    period DATE NOT NULL,
    capacity_mw NUMERIC,
    outage_mw NUMERIC,
    operating_mw NUMERIC,
    percent_outage NUMERIC,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period)
);
