#!/bin/bash
# Run EIA table creation scripts in the ingest database (not the default DB).
# Use POSTGRES_USER so this works when the image is run with a custom superuser (e.g. energy).
set -e
for f in /docker-entrypoint-initdb.d/ingest/*.sql; do
  psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER:-postgres}" -d ingest -f "$f"
done
