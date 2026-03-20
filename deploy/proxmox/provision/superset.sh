#!/usr/bin/env bash
# Run INSIDE the energy-superset LXC container.
# Installs Docker, pulls the Superset image, runs one-shot init,
# then starts the persistent Superset service via systemd.
#
# Usage (from Proxmox host after pushing the repo):
#   pct exec 203 -- bash /opt/energy-usa/deploy/proxmox/provision/superset.sh

set -euo pipefail

REPO_DIR="/opt/energy-usa"
COMPOSE_FILE="$REPO_DIR/deploy/proxmox/compose/superset.yaml"

echo "==> Installing Docker..."
apt-get update -qq
apt-get install -y -qq curl ca-certificates gnupg

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get update -qq
apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin

systemctl enable docker
systemctl start docker

echo "==> Pulling Superset image (this takes a while)..."
docker compose -f "$COMPOSE_FILE" pull superset

echo "==> Running one-shot Superset init..."
# Creates admin user, upgrades metadata DB, seeds datasource connections.
# Safe to re-run — all steps are idempotent.
docker compose -f "$COMPOSE_FILE" run --rm superset-init

echo "==> Starting Superset service..."
docker compose -f "$COMPOSE_FILE" up -d superset

echo "==> Installing systemd service for auto-restart on reboot..."
cat > /etc/systemd/system/energy-superset.service <<EOF
[Unit]
Description=Energy USA - Superset
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$REPO_DIR
ExecStart=docker compose -f $COMPOSE_FILE up -d superset
ExecStop=docker compose -f $COMPOSE_FILE down
TimeoutStartSec=120

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable energy-superset

echo ""
echo "==> Superset provisioning complete."
echo "    URL:   http://$(hostname -I | awk '{print $1}'):8088"
echo "    Login: \$SUPERSET_ADMIN_USER / \$SUPERSET_ADMIN_PASSWORD (from .env)"
echo ""
echo "    To re-run init (e.g. after adding a new DB connection):"
echo "      docker compose -f $COMPOSE_FILE run --rm superset-init"
