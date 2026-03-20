-- Create the Superset database for Apache Superset's metadata (charts, dashboards, users).
SELECT 'CREATE DATABASE superset'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'superset')\gexec