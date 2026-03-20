#!/usr/bin/env bash
# Run this script on the Proxmox HOST (not inside a container).
# Creates three LXC containers: postgres, app (prefect + django), and jupyter.
#
# Usage:
#   bash deploy/proxmox/create-lxc.sh
#
# Prerequisites:
#   1. Download a Debian 12 LXC template on the Proxmox host first:
#      pveam update && pveam download local debian-12-standard_12.7-1_amd64.tar.zst
#   2. Edit the CONFIGURATION section below to match your network and storage.

set -euo pipefail

# =============================================================================
# CONFIGURATION — edit these to match your Proxmox environment
# =============================================================================

# Debian 12 LXC template (run `pveam available --section system` to list)
TEMPLATE="local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst"

# Storage pool for container root disks (run `pvesm status` to list)
STORAGE="local-lvm"

# Network bridge (run `ip link` on Proxmox host to confirm)
BRIDGE="vmbr0"

# Gateway for your LAN
GATEWAY="192.168.1.1"

# Static IPs for each container (must be free on your network)
POSTGRES_IP="192.168.1.10/24"
APP_IP="192.168.1.11/24"
JUPYTER_IP="192.168.1.12/24"

# VM IDs (must not already be in use; run `pct list` to check)
POSTGRES_VMID=200
APP_VMID=201
JUPYTER_VMID=202

# Root password for the containers (change this)
CONTAINER_PASSWORD="changeme"

# SSH public key to allow passwordless root login (optional but recommended)
# Set to empty string "" to skip
SSH_KEY_FILE="/root/.ssh/authorized_keys"

# Resources
POSTGRES_CORES=4;  POSTGRES_MEM=4096;  POSTGRES_DISK=40   # GB
APP_CORES=2;       APP_MEM=2048;       APP_DISK=20         # GB
JUPYTER_CORES=2;   JUPYTER_MEM=4096;   JUPYTER_DISK=20     # GB

# =============================================================================

SSH_KEY_ARGS=()
if [[ -n "$SSH_KEY_FILE" && -f "$SSH_KEY_FILE" ]]; then
  SSH_KEY_ARGS=(--ssh-public-keys "$SSH_KEY_FILE")
fi

create_lxc() {
  local vmid="$1" hostname="$2" ip="$3" cores="$4" mem="$5" disk="$6"
  local privileged="${7:-0}"  # 0 = unprivileged (default)

  echo ""
  echo "==> Creating LXC $vmid ($hostname) at $ip ..."

  pct create "$vmid" "$TEMPLATE" \
    --hostname "$hostname" \
    --cores "$cores" \
    --memory "$mem" \
    --rootfs "$STORAGE:$disk" \
    --net0 "name=eth0,bridge=$BRIDGE,ip=$ip,gw=$GATEWAY" \
    --unprivileged "$((1 - privileged))" \
    --features "nesting=1,keyctl=1" \
    --ostype debian \
    --password "$CONTAINER_PASSWORD" \
    --start 0 \
    "${SSH_KEY_ARGS[@]+"${SSH_KEY_ARGS[@]}"}"

  echo "    Created $vmid ($hostname)"
}

# Create all three containers
create_lxc "$POSTGRES_VMID" "energy-postgres" "$POSTGRES_IP" "$POSTGRES_CORES" "$POSTGRES_MEM" "$POSTGRES_DISK"
create_lxc "$APP_VMID"      "energy-app"      "$APP_IP"      "$APP_CORES"      "$APP_MEM"      "$APP_DISK"
create_lxc "$JUPYTER_VMID"  "energy-jupyter"  "$JUPYTER_IP"  "$JUPYTER_CORES"  "$JUPYTER_MEM"  "$JUPYTER_DISK"

# Start all containers
echo ""
echo "==> Starting containers..."
pct start "$POSTGRES_VMID"
pct start "$APP_VMID"
pct start "$JUPYTER_VMID"

# Give them a moment to boot
sleep 5

echo ""
echo "==> Containers are running:"
pct list | grep -E "^($POSTGRES_VMID|$APP_VMID|$JUPYTER_VMID)\s"

POSTGRES_IP_BARE="${POSTGRES_IP%/*}"
APP_IP_BARE="${APP_IP%/*}"
JUPYTER_IP_BARE="${JUPYTER_IP%/*}"

echo ""
echo "==> Next steps:"
echo ""
echo "  1. Copy the repo and provision scripts into each container:"
echo "       pct push $POSTGRES_VMID deploy/proxmox/provision/postgres.sh /root/provision.sh"
echo "       pct exec $POSTGRES_VMID -- bash /root/provision.sh"
echo ""
echo "       # For app and jupyter, push the full repo:"
echo "       # (or git clone inside the container — see deploy/proxmox/README.md)"
echo ""
echo "  2. Postgres LXC IP: $POSTGRES_IP_BARE"
echo "     Use this as POSTGRES_HOST in deploy/proxmox/.env.production on each LXC."
echo ""
echo "  3. After provisioning, services will be available at:"
echo "       Web dashboard:  http://$APP_IP_BARE:8000"
echo "       Prefect UI:     http://$APP_IP_BARE:4200"
echo "       Jupyter Lab:    http://$JUPYTER_IP_BARE:8888"
echo "       pgweb:          http://$APP_IP_BARE:8080"
echo "       Postgres:       $POSTGRES_IP_BARE:5432"
echo ""
echo "  Full guide: deploy/proxmox/README.md"
