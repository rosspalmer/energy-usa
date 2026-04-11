-- Create all application databases. Runs once on first container start.
-- Order: prefect (Prefect server metadata), ingest (EIA/EPA/FERC raw data),
-- transform (domain models), superset (BI dashboard metadata).

SELECT 'CREATE DATABASE prefect'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'prefect')\gexec

SELECT 'CREATE DATABASE ingest'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'ingest')\gexec

SELECT 'CREATE DATABASE transform'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'transform')\gexec

SELECT 'CREATE DATABASE superset'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'superset')\gexec
