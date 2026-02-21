"""Energy USA: Live and historical US energy data API.

This package provides a FastAPI application that reads data from the U.S. Energy
Information Administration (EIA) API v2 and serves it via REST. It includes
an EIA client, a concurrent API call manager with retries, and config loaded
from the environment. Run the app with::

    uv run uvicorn energy_usa.main:app --reload
"""
