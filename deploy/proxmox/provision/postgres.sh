#!/usr/bin/env bash
# Run INSIDE the postgres LXC container.
# Installs PostgreSQL 16 natively (no Docker), creates all required databases,
# and configures network access so the app and jupyter LXCs can connect.
#
# Usage (from Proxmox host):
#   pct push 200 deploy/proxmox/provision/postgres.sh /root/provision.sh
#   pct exec 200 -- bash /root/provision.sh
#
# Or interactively inside the container:
#   bash /root/provision.sh

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

# CIDR range to allow connections from (should cover app + jupyter LXC IPs).
# Default allows the full /24 subnet. Tighten this if needed.
ALLOWED_CIDR="192.168.1.0/24"

# PostgreSQL superuser for the energy databases
DB_USER="${POSTGRES_USER:-energy}"
DB_PASSWORD="${POSTGRES_PASSWORD:-changeme}"

# =============================================================================

echo "==> Installing PostgreSQL 16..."
apt-get update -qq
apt-get install -y -qq curl gnupg lsb-release

curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
  | gpg --dearmor -o /etc/apt/trusted.gpg.d/postgresql.gpg

echo "deb https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
  > /etc/apt/sources.list.d/pgdg.list

apt-get update -qq
apt-get install -y -qq postgresql-16

echo "==> Configuring PostgreSQL to listen on all interfaces..."
PG_CONF="/etc/postgresql/16/main/postgresql.conf"
PG_HBA="/etc/postgresql/16/main/pg_hba.conf"

sed -i "s/^#listen_addresses = 'localhost'/listen_addresses = '*'/" "$PG_CONF"
# Uncomment if already set to localhost
sed -i "s/^listen_addresses = 'localhost'/listen_addresses = '*'/" "$PG_CONF"

echo "==> Adding pg_hba rule for LAN access ($ALLOWED_CIDR)..."
cat >> "$PG_HBA" <<EOF

# Energy USA: allow app and jupyter LXCs
host    all             $DB_USER        $ALLOWED_CIDR           scram-sha-256
EOF

echo "==> Starting PostgreSQL..."
systemctl enable postgresql
systemctl start postgresql

echo "==> Creating database user and databases..."
su -c "psql -v ON_ERROR_STOP=1" postgres <<SQL
-- Application user
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DB_USER') THEN
    CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
  END IF;
END
\$\$;

-- Django app database
SELECT 'CREATE DATABASE energy_usa OWNER $DB_USER'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'energy_usa')\gexec

-- EIA ingest database
SELECT 'CREATE DATABASE ingest OWNER $DB_USER'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'ingest')\gexec

-- Prefect server metadata database
SELECT 'CREATE DATABASE prefect OWNER $DB_USER'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'prefect')\gexec

GRANT ALL PRIVILEGES ON DATABASE energy_usa TO $DB_USER;
GRANT ALL PRIVILEGES ON DATABASE ingest TO $DB_USER;
GRANT ALL PRIVILEGES ON DATABASE prefect TO $DB_USER;
SQL

echo "==> Reloading PostgreSQL to apply config changes..."
systemctl reload postgresql

echo "==> Copying ingest schema SQL files..."
# These are pushed from the repo by the provision step in README.md
SCHEMA_DIR="/opt/energy-usa/docker/postgres/init/ingest"
if [[ -d "$SCHEMA_DIR" ]]; then
  for f in "$SCHEMA_DIR"/*.sql; do
    echo "    Applying $f ..."
    su -c "psql -v ON_ERROR_STOP=1 -d ingest -f $f" postgres
  done
  echo "    Ingest schema applied."
else
  echo "    WARNING: Schema dir $SCHEMA_DIR not found."
  echo "    Push the repo first, then run:"
  echo "    for f in $SCHEMA_DIR/*.sql; do su -c \"psql -d ingest -f \$f\" postgres; done"
fi

echo ""
echo "==> PostgreSQL provisioning complete."
echo "    Databases: energy_usa, ingest, prefect"
echo "    User:      $DB_USER"
echo "    Listening: 0.0.0.0:5432"
echo "    LAN access: $ALLOWED_CIDR"
