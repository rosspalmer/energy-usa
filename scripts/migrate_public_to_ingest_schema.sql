-- One-time migration for existing deployments: move tables from public to ingest schema.
-- Run against the ingest database before deploying the updated code.
-- Safe to skip on fresh installs (init scripts create tables in ingest schema directly).

DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'eia_retail_sales') THEN
    ALTER TABLE public.eia_retail_sales SET SCHEMA ingest;
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'eia_electric_power_operational') THEN
    ALTER TABLE public.eia_electric_power_operational SET SCHEMA ingest;
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'eia_state_source_disposition') THEN
    ALTER TABLE public.eia_state_source_disposition SET SCHEMA ingest;
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'eia_state_summary') THEN
    ALTER TABLE public.eia_state_summary SET SCHEMA ingest;
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'ingest_dataset_cadence') THEN
    ALTER TABLE public.ingest_dataset_cadence SET SCHEMA ingest;
  END IF;
END $$;
