-- Create the ingest database for EIA API-pulled data (Prefect worker writes here).
SELECT 'CREATE DATABASE ingest'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'ingest')\gexec
