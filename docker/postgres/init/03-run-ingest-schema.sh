#!/bin/bash
# Run EIA table creation scripts in the ingest database (not the default DB).
set -e

# Ensure ingest DB exists even if script order changes or scripts are replayed.
INGEST_EXISTS="$(
  psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER:-postgres}" -d postgres -tAc \
    "SELECT 1 FROM pg_database WHERE datname = 'ingest'"
)"
if [ "$INGEST_EXISTS" != "1" ]; then
  psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER:-postgres}" -d postgres -c "CREATE DATABASE ingest"
fi

for f in /docker-entrypoint-initdb.d/ingest/*.sql; do
  [ -f "$f" ] || continue
  psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER:-postgres}" -d ingest -f "$f"
done
