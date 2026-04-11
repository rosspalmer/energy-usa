-- EIA SEDS (State Energy Data System): annual energy production, consumption, price, expenditure by state.
-- Period stored as DATE (Jan 1 of year).
CREATE TABLE IF NOT EXISTS eia.seds (
    period DATE NOT NULL,
    msn TEXT NOT NULL,
    state_id TEXT NOT NULL,
    state_description TEXT,
    value NUMERIC,
    unit TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, msn, state_id)
);

CREATE INDEX IF NOT EXISTS idx_seds_state ON eia.seds (state_id, period);
CREATE INDEX IF NOT EXISTS idx_seds_msn ON eia.seds (msn);
