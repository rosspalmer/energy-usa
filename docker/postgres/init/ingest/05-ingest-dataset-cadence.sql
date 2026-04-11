-- Metadata table for EIA ingest datasets: cadence and deployment info.
-- One row per dataset; used to document and drive run/source cadence.
CREATE TABLE IF NOT EXISTS ingest.ingest_dataset_cadence (
    dataset_key TEXT NOT NULL PRIMARY KEY,
    target_table TEXT NOT NULL,
    source_frequency TEXT NOT NULL,
    period_cadence TEXT NOT NULL,
    run_cadence TEXT NOT NULL,
    deployment_name TEXT NOT NULL,
    flow_name TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT true
);

COMMENT ON TABLE ingest.ingest_dataset_cadence IS 'Per-dataset cadence and deployment metadata for EIA electricity ingest.';
COMMENT ON COLUMN ingest.ingest_dataset_cadence.source_frequency IS 'EIA API data grain: monthly or annual.';
COMMENT ON COLUMN ingest.ingest_dataset_cadence.period_cadence IS 'Stored period grain: monthly (first day of month) or yearly (Jan 1).';
COMMENT ON COLUMN ingest.ingest_dataset_cadence.run_cadence IS 'Schedule cadence for this ingest job: monthly, etc.';

INSERT INTO ingest.ingest_dataset_cadence (
    dataset_key,
    target_table,
    source_frequency,
    period_cadence,
    run_cadence,
    deployment_name,
    flow_name,
    enabled
) VALUES
    (
        'retail_sales',
        'eia_retail_sales',
        'monthly',
        'monthly',
        'monthly',
        'ingest-eia-retail-sales',
        'ingest-eia-retail-sales',
        true
    ),
    (
        'electric_power_operational',
        'eia_electric_power_operational',
        'monthly',
        'monthly',
        'monthly',
        'ingest-eia-electric-power-operational',
        'ingest-eia-electric-power-operational',
        true
    ),
    (
        'state_source_disposition',
        'eia_state_source_disposition',
        'monthly',
        'monthly',
        'monthly',
        'ingest-eia-state-source-disposition',
        'ingest-eia-state-source-disposition',
        true
    ),
    (
        'state_summary',
        'eia_state_summary',
        'annual',
        'yearly',
        'monthly',
        'ingest-eia-state-summary',
        'ingest-eia-state-summary',
        true
    )
ON CONFLICT (dataset_key) DO NOTHING;
