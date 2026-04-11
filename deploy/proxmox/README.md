# Proxmox LXC Deployment Guide

This guide walks through deploying Energy USA on a Proxmox server using LXC containers.

## What Gets Created

Four LXC containers, each with a dedicated job:

| Container | Default IP | What it runs |
|-----------|-----------|--------------|
| `energy-postgres` | 192.168.1.10 | PostgreSQL 16 (native, no Docker) |
| `energy-app` | 192.168.1.11 | Prefect server + worker, pgweb |
| `energy-jupyter` | 192.168.1.12 | Jupyter Lab |
| `energy-superset` | 192.168.1.13 | Apache Superset BI dashboard |

Postgres is isolated in its own container so it can be given dedicated CPU/RAM resources and managed independently (backups, upgrades) without touching the app.

## Prerequisites

- Proxmox VE 8+ installed and running
- SSH access to the Proxmox host as `root`
- A Debian 12 LXC template downloaded on the host (step 1 below)
- The repo cloned somewhere on a machine you can work from

---

## Step 1 — Download the Debian 12 Template (Proxmox host)

```bash
# SSH into the Proxmox host, then:
pveam update
pveam download local debian-12-standard_12.7-1_amd64.tar.zst
```

> Run `pveam available --section system | grep debian-12` if you want to check the exact filename — it may have a newer version number.

---

## Step 2 — Edit the Create Script

Open `deploy/proxmox/create-lxc.sh` on your workstation and edit the **CONFIGURATION** section at the top:

- **`GATEWAY`** — your router's IP (e.g. `192.168.1.1`)
- **`POSTGRES_IP` / `APP_IP` / `JUPYTER_IP`** — choose free static IPs on your LAN
- **`STORAGE`** — Proxmox storage pool name (run `pvesm status` on the Proxmox host to check; often `local-lvm`)
- **`CONTAINER_PASSWORD`** — root password for the containers
- **`SSH_KEY_FILE`** — path to your public key on the Proxmox host (recommended for passwordless SSH)

---

## Step 3 — Create the Containers (Proxmox host)

Copy the script to the Proxmox host and run it:

```bash
# From your workstation
scp deploy/proxmox/create-lxc.sh root@<proxmox-ip>:/root/

# On the Proxmox host
bash /root/create-lxc.sh
```

This creates and starts all three containers. You can verify with `pct list`.

---

## Step 4 — Push the Repo to Each Container

The app, jupyter, and superset containers need the full repo. The postgres container only needs the schema SQL files.

```bash
# From your workstation — adjust paths and IPs to match your config

# Push schema files to postgres container (VMID 200)
pct exec 200 -- mkdir -p /opt/energy-usa/docker/postgres/init/ingest
for f in docker/postgres/init/ingest/*.sql; do
  pct push 200 "$f" "/opt/energy-usa/$f"
done

# Clone the full repo into app container (VMID 201)
# Option A: if the repo is on a git remote (GitHub, Gitea, etc.)
pct exec 201 -- bash -c "apt-get install -y git && git clone <your-repo-url> /opt/energy-usa"

# Option B: rsync from your workstation (no remote required)
pct exec 201 -- mkdir -p /opt/energy-usa
rsync -av --exclude='.git' --exclude='__pycache__' ./ root@192.168.1.11:/opt/energy-usa/

# Same for jupyter container (VMID 202)
pct exec 202 -- mkdir -p /opt/energy-usa
rsync -av --exclude='.git' --exclude='__pycache__' ./ root@192.168.1.12:/opt/energy-usa/

# Same for superset container (VMID 203)
pct exec 203 -- mkdir -p /opt/energy-usa
rsync -av --exclude='.git' --exclude='__pycache__' ./ root@192.168.1.13:/opt/energy-usa/
```

---

## Step 5 — Create the .env File on Each Container

The app, jupyter, and superset containers each need a `.env` file at `/opt/energy-usa/.env`.

```bash
# On the app container (192.168.1.11)
ssh root@192.168.1.11
cp /opt/energy-usa/deploy/proxmox/.env.production.example /opt/energy-usa/.env
nano /opt/energy-usa/.env
# Fill in: EIA_API_KEY, POSTGRES_HOST, POSTGRES_PASSWORD, ANTHROPIC_API_KEY

# On the jupyter container (192.168.1.12) — same process
ssh root@192.168.1.12
cp /opt/energy-usa/deploy/proxmox/.env.production.example /opt/energy-usa/.env
nano /opt/energy-usa/.env

# On the superset container (192.168.1.13)
ssh root@192.168.1.13
cp /opt/energy-usa/deploy/proxmox/.env.production.example /opt/energy-usa/.env
nano /opt/energy-usa/.env
# Fill in: POSTGRES_HOST, POSTGRES_PASSWORD, SUPERSET_SECRET_KEY,
#          SUPERSET_ADMIN_PASSWORD (and optionally SUPERSET_COOKIE_SECURE,
#          SUPERSET_PROXY_FIX if behind a reverse proxy)
```

Key values to set (see `.env.production.example` for all options):

| Variable | What to set |
|----------|------------|
| `POSTGRES_HOST` | IP of the postgres container (e.g. `192.168.1.10`) |
| `POSTGRES_PASSWORD` | Strong password — must match what you set in step 6 |
| `EIA_API_KEY` | Your EIA API key |
| `ANTHROPIC_API_KEY` | For jupyter-ai Claude integration |
| `SUPERSET_SECRET_KEY` | Run `python -c "import secrets; print(secrets.token_hex(42))"` |
| `SUPERSET_ADMIN_PASSWORD` | Strong password for the Superset admin UI login |

---

## Step 6 — Provision Postgres (postgres container)

```bash
ssh root@192.168.1.10

# Run the provisioning script
# (edit ALLOWED_CIDR and DB_PASSWORD at the top to match your .env)
bash /opt/energy-usa/deploy/proxmox/provision/postgres.sh
```

The script will:
- Install PostgreSQL 16
- Create databases: `ingest`, `prefect`, `superset`
- Create the `energy` user with the password you set
- Open port 5432 to your LAN subnet
- Apply the ingest table schemas

---

## Step 7 — Provision App (app container)

```bash
ssh root@192.168.1.11
bash /opt/energy-usa/deploy/proxmox/provision/app.sh
```

This installs Docker, builds the images, starts the services, creates the Prefect work pool, and registers the ingest deployments. It also installs a systemd service so everything restarts automatically after a reboot.

---

## Step 8 — Provision Jupyter (jupyter container)

```bash
ssh root@192.168.1.12
bash /opt/energy-usa/deploy/proxmox/provision/jupyter.sh
```

---

## Step 9 — Provision Superset (superset container)

```bash
ssh root@192.168.1.13
cd /opt/energy-usa
bash deploy/proxmox/provision/superset.sh
```

This installs Docker, pulls the Superset image, runs one-shot init (creates admin user, seeds the `EIA Ingest` and `Energy USA App` database connections), and starts the persistent service under systemd.

**Authentication**: Superset uses username/password login by default. Log in with `SUPERSET_ADMIN_USER` / `SUPERSET_ADMIN_PASSWORD` from your `.env`. The `EIA Ingest` datasource (pointing at the `ingest` database) is pre-connected — go to **SQL Lab → SQL Editor** or **Data → Datasets** to start building charts.

**Internet-facing setup**: If exposing Superset publicly, consider putting it behind a TLS-terminating reverse proxy (Caddy, nginx). Set `SUPERSET_PROXY_FIX=true` and `SUPERSET_COOKIE_SECURE=true` in `.env`, then re-run init:
```bash
docker compose -f deploy/proxmox/compose/superset.yaml run --rm superset-init
docker compose -f deploy/proxmox/compose/superset.yaml restart superset
```

---

## Step 10 — Run the Initial Data Backfill

Once everything is running, trigger a backfill from **your workstation** (or from inside the app container):

```bash
# From the app container
ssh root@192.168.1.11
cd /opt/energy-usa
PREFECT_API_URL=http://localhost:4200/api \
  docker compose -f deploy/proxmox/compose/app.yaml \
  run --rm prefect-worker \
  prefect deployment run backfill-eia/backfill-eia \
  --param date_start=2015-01 --param date_end=2024-12 --param dataset=all
```

Monitor progress in the Prefect UI at `http://192.168.1.11:4200`.

---

## Service URLs (after provisioning)

| Service | URL |
|---------|-----|
| Prefect UI | http://192.168.1.11:4200 |
| pgweb (Postgres browser) | http://192.168.1.11:8080 |
| Jupyter Lab | http://192.168.1.12:8888 |
| Superset | http://192.168.1.13:8088 |
| Postgres | 192.168.1.10:5432 |

---

## Updating the App

To deploy a new version of the code:

```bash
ssh root@192.168.1.11
cd /opt/energy-usa
git pull   # or rsync from workstation
docker compose -f deploy/proxmox/compose/app.yaml up -d --build
```

Same process on the jupyter and superset containers:

```bash
# Jupyter
ssh root@192.168.1.12
cd /opt/energy-usa && git pull
docker compose -f deploy/proxmox/compose/jupyter.yaml up -d --build

# Superset (image is upstream — no --build needed)
ssh root@192.168.1.13
cd /opt/energy-usa && git pull
docker compose -f deploy/proxmox/compose/superset.yaml pull
docker compose -f deploy/proxmox/compose/superset.yaml up -d superset
```

---

## Connecting DBeaver to Postgres

From your workstation, DBeaver can connect directly to the postgres container:

1. New Connection → **PostgreSQL**
2. Host: `192.168.1.10`, Port: `5432`
3. Database: `ingest`
4. Username / Password: from your `.env`
5. Test Connection → Finish

---

## Useful Container Management Commands

All run on the **Proxmox host**:

```bash
pct list                          # List containers and status
pct start 200                     # Start postgres container
pct stop 201                      # Stop app container
pct exec 201 -- docker ps         # Check running Docker services in app container
pct exec 200 -- systemctl status postgresql   # Check Postgres status
pct console 201                   # Open interactive console (Ctrl+] to exit)
```

---

## Troubleshooting

**App can't connect to Postgres**
- Check `POSTGRES_HOST` in `.env` matches the postgres container IP
- Verify Postgres is running: `pct exec 200 -- systemctl status postgresql`
- Check `pg_hba.conf` allows the app container IP: `pct exec 200 -- cat /etc/postgresql/16/main/pg_hba.conf`

**Docker fails inside LXC**
- Confirm the container has `features: nesting=1,keyctl=1` in its config: `cat /etc/pve/lxc/201.conf`
- If missing: `pct stop 201 && pct set 201 --features nesting=1,keyctl=1 && pct start 201`

**Prefect worker not picking up jobs**
- Check it's connected to the right server: `PREFECT_API_URL` should be `http://prefect-server:4200/api` (Docker internal) inside the app compose
- Verify the work pool exists: open Prefect UI → Work Pools

**Jupyter can't reach Postgres**
- Same as app — verify `POSTGRES_HOST` in the jupyter container's `.env`
