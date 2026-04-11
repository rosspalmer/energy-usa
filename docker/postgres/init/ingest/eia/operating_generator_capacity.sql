-- EIA electricity/operating-generator-capacity: monthly installed capacity per generator.
-- Period stored as DATE (first of month).
CREATE TABLE IF NOT EXISTS eia.operating_generator_capacity (
    period DATE NOT NULL,
    plantid TEXT NOT NULL,
    generatorid TEXT NOT NULL,
    stateid TEXT,
    entity_id TEXT,
    entity_name TEXT,
    energy_source_code TEXT,
    prime_mover_code TEXT,
    nameplate_capacity_mw NUMERIC,
    net_summer_capacity_mw NUMERIC,
    net_winter_capacity_mw NUMERIC,
    operating_year TEXT,
    technology TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, plantid, generatorid)
);

CREATE INDEX IF NOT EXISTS idx_eia_gen_capacity_state ON eia.operating_generator_capacity (stateid, period);
