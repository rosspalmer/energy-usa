# Getting Started

This guide walks through setting up Energy USA from scratch — from zero to having data in the database and the dashboard running. There are two paths: **full Docker stack** (everything in containers, closest to production) and **local-only** (lighter, faster to start, easier to debug).

---

## What you need to install first

These are one-time installs. If you're on macOS, all of these install via a single terminal command.

### 1. Homebrew (macOS package manager)

If you don't have it:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. `uv` (Python package manager)

This project uses `uv` instead of `pip`. It handles Python versions and dependencies automatically.

```bash
brew install uv
```

### 3. `make`

Used to run common project commands. Usually already installed; if not:
```bash
xcode-select --install
```

### 4. Docker Desktop (for the full stack only)

Download from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/). After installing, open Docker Desktop and let it finish starting up before continuing.

---

## Get an EIA API key

The project pulls data from the U.S. Energy Information Administration (EIA) API. Registration is free and instant.

1. Go to [eia.gov/opendata/register.php](https://www.eia.gov/opendata/register.php)
2. Fill in your name and email
3. Copy the API key from the confirmation email — you'll need it in the next step

---

## Configure your environment

The project reads configuration from a `.env` file in the project root.

```bash
cp .env.example .env
```

Open `.env` in any text editor and fill in:

| Variable | What to set |
|----------|------------|
| `EIA_API_KEY` | Your EIA key from above |
| `ANTHROPIC_API_KEY` | Optional — only needed if you want Claude AI in Jupyter. Get one at [console.anthropic.com](https://console.anthropic.com) |

Everything else can stay as the default for local development.

---

## Option A: Full Docker stack

This runs everything (database, ingest scheduler, web app, Jupyter) in Docker containers. Closest to how the production server works.

```bash
# Start all services
make up
```

The first time you run this, Docker will download and build images — it takes a few minutes. You'll see a lot of output. When it settles, all services are running.

**Check that it worked** by opening these in your browser:
- Dashboard: http://localhost:8000
- Prefect UI (job scheduler): http://localhost:4200
- Jupyter Lab: http://localhost:8888
- Database browser: http://localhost:8080

### Load historical data

The database starts empty. Run a backfill to load EIA data:

```bash
# Load retail electricity sales data for 2020–2024
make backfill DATASET=retail_sales START=2020-01 END=2024-12

# Load all four datasets at once (takes longer)
make backfill DATASET=all START=2015-01 END=2024-12
```

This runs the ingest directly on your machine (no Prefect server needed) and prints progress to your terminal. When it finishes, refresh the dashboard — you should see charts with data.

### Stopping the stack

```bash
make down
```

Your database data is preserved in a Docker volume — it'll still be there when you `make up` again.

---

## Option B: Local-only (lighter)

Skips Docker. Runs the ingest and web app directly on your machine, connecting to a local Postgres database.

### Install Postgres locally

```bash
brew install postgresql@16
brew services start postgresql@16
```

Create the databases:
```bash
createdb energy_usa
createdb ingest
createdb prefect
```

Apply the ingest schema:
```bash
for f in docker/postgres/init/ingest/*.sql; do
  psql -d ingest -f "$f"
done
```

Update `.env` to point to your local Postgres (the defaults should already work):
```
DATABASE_URL=postgresql://localhost:5432/energy_usa
INGEST_DATABASE_URL=postgresql://localhost:5432/ingest
```

### Load data

```bash
make backfill DATASET=retail_sales START=2020-01 END=2024-12
```

### Start the web app

```bash
make web
```

Open http://localhost:8000.

---

## What's in the database?

After a backfill, you'll have four tables in the `ingest` database:

| Table | What it contains | Frequency |
|-------|-----------------|-----------|
| `eia_retail_sales` | Electricity sales, revenue, price, and customers by state and sector | Monthly |
| `eia_electric_power_operational` | Electricity generation by state, sector, and fuel type | Monthly |
| `eia_state_source_disposition` | Net interstate electricity trade and total disposition by state | Monthly |
| `eia_state_summary` | Annual summary: retail price, total generation, total consumption by state | Annual |

See [Analyzing Data](data-analysis.md) for how to query and explore this data.

---

## Troubleshooting

**`make up` fails with a proxy error**

Docker is trying to route image downloads through a proxy. Fix: Docker Desktop → Settings → Resources → Proxies → turn off Manual proxy configuration. Restart Docker Desktop, then try again.

**`EIA_API_KEY` not set error**

Check that `.env` exists in the project root (not `.env.example`) and that `EIA_API_KEY=` is filled in with your key (no spaces, no quotes).

**Database connection refused**

If using the Docker stack, make sure `make up` completed successfully before running `make backfill`. If local-only, check that `postgresql@16` is running: `brew services list | grep postgresql`.

**Port already in use**

Something else is using port 5432 (Postgres), 8000 (web), or 4200 (Prefect). Stop the conflicting process, or change the port mapping in `compose.yaml`.
