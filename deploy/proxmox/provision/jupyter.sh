#!/usr/bin/env bash
# Run INSIDE the jupyter LXC container (energy-jupyter).
# Installs Docker, clones the repo, and starts Jupyter Lab via Docker Compose.
#
# Usage (from Proxmox host):
#   pct exec 202 -- bash -c "apt-get install -y git curl && \
#     git clone <your-repo-url> /opt/energy-usa && \
#     bash /opt/energy-usa/deploy/proxmox/provision/jupyter.sh"
#
# Requires /opt/energy-usa/.env to exist before running.

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

echo "==> Building and starting Jupyter service..."
docker compose -f deploy/proxmox/compose/jupyter.yaml up -d --build

echo ""
echo "==> Installing systemd service for auto-start on boot..."
cat > /etc/systemd/system/energy-jupyter.service <<EOF
[Unit]
Description=Energy USA Jupyter Lab
After=network-online.target docker.service
Wants=network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$REPO_DIR
ExecStart=docker compose -f deploy/proxmox/compose/jupyter.yaml up -d
ExecStop=docker compose -f deploy/proxmox/compose/jupyter.yaml down
TimeoutStartSec=120

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable energy-jupyter

echo ""
echo "==> Jupyter provisioning complete."
echo "    Jupyter Lab: http://$(hostname -I | awk '{print $1}'):8888"
echo ""
echo "    NOTE: Jupyter has no password by default — restrict access at the"
echo "    network/firewall level or set ServerApp.token in the compose file."
