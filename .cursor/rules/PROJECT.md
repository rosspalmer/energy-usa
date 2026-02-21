# Project Description

## Core features

- Live and historical data reader RestAPI
- Fast database correlating data points on a regional level
- Clean and fun interactive UI for exploring the data

## Tech Stack

- Python + FastAPI application for reading, transforming, and serving data
    - Use uv as a package manager
- Postgres SQL database for storing data cleaned data
- Web UI????
- Docker compose setup

## API Reader

1. Build a multithreaded API call manager
2. Make connections to Energy Information Administration (EIA) API
    - /electricity
    - /natural-gas
    - /petroleum
    - /coal
    - /total-energy

## Database

1. Setup a postgres database
2. Create electricity schema
    - Add prices table
    - Add consumption table