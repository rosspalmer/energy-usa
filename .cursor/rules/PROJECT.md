# Project Description

## Core features

- Live and historical data reader RestAPI
- Fast database correlating data points on a regional level
- Clean and fun interactive UI for exploring the data

## Tech Stack

- Use Python with uv as package manager
- Python + FastAPI application for reading and serving data
    - Use uv as a package manager
- Prefect orchestrator 
- Postgres SQL database for storing data cleaned data
- Django app with Dash (plotly) dashboarding
- Docker compose setup

## API and Data Service

- Multithreaded API call manager used to retreive data from external services
- Deposit returned results into postgres database (`ingest`) [Schedule with prefect]
- Run transformations in postgres to generate dashboard tables (`display`) [Schedule with prefect]
- Pull in data at a monthly cadence whenever possible elsewise quarterly or daily

### External Data APIs

- Energy Information Administration (EIA) API: 
    - /electricity (use subpath `retail-sales/data` for time-series data rows; without `/data` the API returns dataset metadata only)
    - /natural-gas
    - /petroleum
    - /coal
    - /total-energy

### Ingest and Docker

- A single Prefect ingest job fetches EIA electricity retail-sales data (`retail-sales/data`) and upserts into Postgres (`eia_retail_sales`). No transformation or display jobs in the initial setup.
- Docker Compose runs Postgres, Prefect server, a Prefect process worker, and the FastAPI service on a single machine; see `compose.yaml` and `.env.example`.

## Django Web App

- Theme should be styled off a retro gas station 
    - bright reds and teal blues with white background
    - Rounded lines 50s car style shapes
    - Use gas station signs as inspiration for icons
    - A bright daytime theme and a warm but early evening like dark theme
- Display dashboard (plotly dash) pages with top line selector
    - Show electricity prices for a persons region over time with ability to compare neighbors