"""FastAPI application entrypoint and lifecycle.

This module creates the main FastAPI app, wires the EIA API call manager
into app state at startup, mounts the data router under ``/api/data``,
and provides a health check at ``/health``. Run with::

    uv run uvicorn energy_usa.main:app --reload
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from energy_usa.config import Settings
from energy_usa.eia.manager import EIAManager
from energy_usa.routers import data


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create the EIA manager at startup and close it on shutdown.

    The manager is stored on ``app.state.eia_manager`` so route dependencies
    can access it. Closing the manager releases the shared HTTP client and
    prevents resource leaks when the server stops.

    :param app: The FastAPI application instance (receives state).
    :yields: None; control returns to the caller while the app is serving.
    """
    settings = Settings()
    app.state.settings = settings
    app.state.eia_manager = EIAManager(
        base_url=settings.eia_base_url,
        api_key=settings.eia_api_key,
        timeout=settings.eia_request_timeout_seconds,
        max_concurrent=settings.eia_max_concurrent_requests,
        max_retries=settings.eia_max_retries,
    )
    yield
    if hasattr(app.state, "eia_manager") and app.state.eia_manager is not None:
        await app.state.eia_manager.aclose()


app = FastAPI(
    title="Energy USA",
    description="Live and historical US energy data API",
    lifespan=lifespan,
)

app.include_router(data.router, prefix="/api/data", tags=["data"])


@app.get("/health")
async def health() -> dict[str, str]:
    """Return a simple health status without calling external services.

    Intended for load balancers, Docker healthchecks, and orchestration.
    A 200 response with ``{"status": "ok"}`` indicates the app is running;
    it does not verify EIA API connectivity or database availability.

    :returns: A dict with key ``status`` and value ``ok``.
    """
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "energy_usa.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
