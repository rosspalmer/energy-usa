-- One-time migration: move tables from ingest.eia_* to eia.* schema.
-- Run against the ingest database:
--   psql -U energy -d ingest -f deploy/migrations/001-rename-eia-schemas.sql
--
-- Safe to run multiple times (IF NOT EXISTS / IF EXISTS guards).

BEGIN;

-- Create the eia schema
CREATE SCHEMA IF NOT EXISTS eia;

-- Create the quality schema
CREATE SCHEMA IF NOT EXISTS quality;

-- Move and rename each table
DO $$
DECLARE
    tbl TEXT;
    old_name TEXT;
    new_name TEXT;
    tables TEXT[] := ARRAY[
        'retail_sales', 'electric_power_operational', 'state_source_disposition',
        'state_summary', 'rto_region_data', 'rto_fuel_type_data',
        'rto_region_sub_ba_data', 'rto_interchange_data', 'rto_daily_region_data',
        'facility_fuel', 'operating_generator_capacity', 'sep_emissions',
        'sep_capability', 'sep_net_metering', 'coal_aggregate_production',
        'coal_consumption_quality', 'coal_mine_production', 'crude_oil_imports',
        'nuclear_outages_us', 'nuclear_outages_facility', 'co2_emissions',
        'natural_gas_prices', 'natural_gas_consumption', 'natural_gas_production',
        'natural_gas_storage', 'petroleum_prices', 'petroleum_supply',
        'total_energy', 'seds', 'steo', 'international',
        'biomass_capacity', 'biomass_production', 'aeo', 'ieo'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables LOOP
        old_name := 'ingest.eia_' || tbl;
        new_name := tbl;
        -- Move to eia schema, then rename to strip prefix
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'ingest' AND table_name = 'eia_' || tbl) THEN
            EXECUTE format('ALTER TABLE %s SET SCHEMA eia', old_name);
            EXECUTE format('ALTER TABLE eia.eia_%s RENAME TO %s', tbl, new_name);
            RAISE NOTICE 'Migrated: ingest.eia_% → eia.%', tbl, tbl;
        END IF;
    END LOOP;

    -- Handle ingest_dataset_cadence → eia.dataset_cadence
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'ingest' AND table_name = 'ingest_dataset_cadence') THEN
        ALTER TABLE ingest.ingest_dataset_cadence SET SCHEMA eia;
        ALTER TABLE eia.ingest_dataset_cadence RENAME TO dataset_cadence;
        RAISE NOTICE 'Migrated: ingest.ingest_dataset_cadence → eia.dataset_cadence';
    END IF;
END $$;

-- Create quality tables (same as 00-quality-schema.sql)
CREATE TABLE IF NOT EXISTS quality.audit_rules (
    rule_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    dataset TEXT NOT NULL,
    check_type TEXT NOT NULL,
    column_name TEXT,
    threshold JSONB NOT NULL,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS quality.audit_results (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    rule_id TEXT REFERENCES quality.audit_rules(rule_id),
    run_id TEXT NOT NULL,
    status TEXT NOT NULL,
    measured_value JSONB,
    detail TEXT,
    checked_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_results_rule
    ON quality.audit_results(rule_id, checked_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_results_run
    ON quality.audit_results(run_id);

-- Drop old ingest schema if empty
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'ingest') THEN
        DROP SCHEMA IF EXISTS ingest;
        RAISE NOTICE 'Dropped empty ingest schema';
    ELSE
        RAISE NOTICE 'ingest schema still has tables — not dropping';
    END IF;
END $$;

COMMIT;
