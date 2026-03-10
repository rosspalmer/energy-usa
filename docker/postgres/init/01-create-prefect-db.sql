-- Create the Prefect database for Prefect Server's API (optional; used when PREFECT_API_DATABASE_CONNECTION_URL points to Postgres).
SELECT 'CREATE DATABASE prefect'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'prefect')\gexec
