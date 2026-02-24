#!/bin/bash
# Run EIA table creation scripts in the ingest database (not the default DB).
set -e
for f in /docker-entrypoint-initdb.d/ingest/*.sql; do
  psql -v ON_ERROR_STOP=1 -d ingest -f "$f"
done
