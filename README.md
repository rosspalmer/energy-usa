# Energy USA

Live and historical US energy data API (FastAPI + EIA).

## Setup

Requires [uv](https://docs.astral.sh/uv/). Get an EIA API key from [EIA Open Data](https://www.eia.gov/opendata/register.php) and set:

- `EIA_API_KEY` – required for EIA API v2
- `EIA_BASE_URL` – optional (defaults to EIA API v2 base)

## Run

```bash
uv run uvicorn energy_usa.main:app --reload
```
