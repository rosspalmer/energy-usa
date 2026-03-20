#!/usr/bin/env bash
# Superset one-shot init container.
# Runs once: upgrades the metadata DB, creates admin user, seeds datasource connections.
# Called by the superset-init service in docker-compose; the main superset service
# uses condition: service_completed_successfully so it only starts after this exits 0.

set -euo pipefail

echo "==> Waiting for Postgres to be ready..."
until python - <<'EOF'
import os, sys, psycopg2
try:
    c = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname="superset",
    )
    c.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
EOF
do
  echo "    ...not ready, retrying in 3s"
  sleep 3
done
echo "    Postgres is ready."

echo "==> Running superset db upgrade..."
superset db upgrade

echo "==> Creating admin user..."
superset fab create-admin \
  --username  "${SUPERSET_ADMIN_USER:-admin}" \
  --firstname "Admin" \
  --lastname  "User" \
  --email     "${SUPERSET_ADMIN_EMAIL:-admin@energy.local}" \
  --password  "${SUPERSET_ADMIN_PASSWORD}" \
  2>/dev/null || echo "    (admin user already exists — skipping)"

echo "==> Running superset init (default roles and permissions)..."
superset init

echo "==> Seeding database connections..."
python /app/pythonpath/seed_databases.py

echo "==> Superset initialisation complete."
