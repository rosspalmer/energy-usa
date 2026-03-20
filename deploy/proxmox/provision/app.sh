#!/usr/bin/env bash
# Run INSIDE the app LXC container (energy-app).
# Installs Docker, clones the repo, and starts the app services
# (Prefect server, Prefect worker, Django web, pgweb) via Docker Compose.
#
# Usage (from Proxmox host):
#   pct exec 201 -- bash -c "apt-get install -y git curl && \
#     git clone <your-repo-url> /opt/energy-usa && \
#     bash /opt/energy-usa/deploy/proxmox/provision/app.sh"
#
# Requires /opt/energy-usa/.env to exist before running (copy .env.production.example).

set -euo pipefail

REPO_DIR="/opt/energy-usa"

echo "==> Installing Docker..."
apt-get update -qq
apt-get install -y -qq ca-certificates curl gnupg

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get update -qq
apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin

systemctl enable docker
systemctl start docker

echo "==> Checking repo at $REPO_DIR..."
if [[ ! -d "$REPO_DIR" ]]; then
  echo "ERROR: $REPO_DIR not found. Clone the repo first:"
  echo "  git clone <your-repo-url> $REPO_DIR"
  exit 1
fi

cd "$REPO_DIR"

echo "==> Checking .env file..."
if [[ ! -f ".env" ]]; then
  echo "ERROR: .env not found in $REPO_DIR"
  echo "Copy and fill in the production env file first:"
  echo "  cp deploy/proxmox/.env.production.example .env"
  echo "  nano .env"
  exit 1
fi

echo "==> Building and starting app services..."
docker compose -f deploy/proxmox/compose/app.yaml up -d --build

echo ""
echo "==> Waiting for services to be ready (up to 60s)..."
sleep 10
docker compose -f deploy/proxmox/compose/app.yaml ps

echo ""
echo "==> Creating Prefect work pool (safe to re-run)..."
docker compose -f deploy/proxmox/compose/app.yaml \
  run --rm prefect-worker \
  prefect work-pool create process-pool --type process 2>/dev/null || true

echo ""
echo "==> Registering Prefect deployments..."
docker compose -f deploy/proxmox/compose/app.yaml \
  run --rm prefect-worker \
  python scripts/deploy_ingest.py

echo ""
echo "==> Installing systemd service for auto-start on boot..."
cat > /etc/systemd/system/energy-app.service <<EOF
[Unit]
Description=Energy USA App Services
After=network-online.target docker.service
Wants=network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$REPO_DIR
ExecStart=docker compose -f deploy/proxmox/compose/app.yaml up -d
ExecStop=docker compose -f deploy/proxmox/compose/app.yaml down
TimeoutStartSec=120

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable energy-app

echo ""
echo "==> App provisioning complete."
echo "    Web dashboard: http://$(hostname -I | awk '{print $1}'):8000"
echo "    Prefect UI:    http://$(hostname -I | awk '{print $1}'):4200"
echo "    pgweb:         http://$(hostname -I | awk '{print $1}'):8080"
