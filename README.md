# Energy USA

Live and historical US energy data API (FastAPI + EIA).

## Setup

1. Install [uv](https://docs.astral.sh/uv/)
2. Get an EIA API key from [EIA Open Data](https://www.eia.gov/opendata/register.php)
3. Create and populate `.env` in project directory using `.env.example` template
    - `cp .env.example .env`
    - Must update `EIA_API_KEY` with key from #2
    - May set custom postgres username/password (OPTIONAL)

## Docker Compose

Run Postgres, Prefect server, Prefect worker, the API, and pgweb (Postgres browser) on one machine:

```bash
docker compose up -d
```

- API: http://localhost:8000  
- Prefect UI: http://localhost:4200  
- pgweb (Postgres browser): http://localhost:8080  

Create the process work pool once so the worker can run flows:

```bash
docker compose run --rm prefect-worker prefect work-pool create process-pool --type process
```

Then deploy the ingest flow (from your host with `uv run` and `PREFECT_API_URL=http://localhost:4200/api`), or run it ad hoc from the Prefect UI.

## License

This project is licensed under the GNU Affero General Public License v3.0.
See LICENSE file for details.
