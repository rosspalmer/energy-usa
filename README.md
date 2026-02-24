# Energy USA

Live and historical US energy data in Postgres (ingested via Prefect from EIA). Web app: Django with Dash (plotly) dashboard.

## Setup

1. Install [uv](https://docs.astral.sh/uv/)
2. Get an EIA API key from [EIA Open Data](https://www.eia.gov/opendata/register.php)
3. Create and populate `.env` in project directory using `.env.example` template
    - `cp .env.example .env`
    - Must update `EIA_API_KEY` with key from #2
    - May set custom postgres username/password (OPTIONAL)

## Docker Compose

Use **`./dock.sh`** to manage the stack (or run `docker compose` directly):

```bash
./dock.sh up              # Start all services
./dock.sh worker-pool     # Create Prefect process work pool (only needed once)
./dock.sh deploy          # Register ingest deployments
./dock.sh run ingest-eia-electricity-all   # Trigger a run
./dock.sh logs [service]  # Tail logs; ./dock.sh help for all commands
```

- **Django web app** (dashboard): http://localhost:8000  
- **Prefect UI** (job orchestration): http://localhost:4200  
- **pgweb** (Postgres browser): http://localhost:8080  

To run the web app locally (with Postgres and data already present):  
`uv sync --extra web` then `PYTHONPATH=web uv run python web/manage.py runserver`. Set `DATABASE_URL` in `.env` or the environment.

Or without the script: `docker compose up -d`, then create the work pool and run `PREFECT_API_URL=http://localhost:4200/api uv run python scripts/deploy_ingest.py` to deploy jobs.


## License

This project is licensed under the GNU Affero General Public License v3.0.
See LICENSE file for details.
