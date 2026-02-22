"""Data router: EIA-backed endpoints.

This router exposes HTTP endpoints that proxy to the EIA API via the shared
:class:`EIAManager`. All EIA access goes through the manager so that
concurrency, retries, and timeouts are applied consistently. Requires
``EIA_API_KEY`` to be set for successful responses from EIA.
"""

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from energy_usa.eia.manager import EIAManager

router = APIRouter()


def get_eia_manager(request: Request) -> EIAManager:
    """FastAPI dependency that returns the shared EIA manager from app state.

    The manager is created during application startup (see :func:`energy_usa.main.lifespan`)
    and stored as ``request.app.state.eia_manager``. Use this dependency in
    route handlers that need to call the EIA API.

    :param request: The current FastAPI request (used to access app state).
    :returns: The application's single :class:`EIAManager` instance.
    """
    return request.app.state.eia_manager


@router.get("/electricity")
async def get_electricity(
    subpath: str = "",
    state_id: str | None = None,
    sector_id: str | None = None,
    length: int | None = None,
    offset: int | None = None,
    manager: EIAManager = Depends(get_eia_manager),
) -> dict[str, Any]:
    """Return electricity data from the EIA API (e.g. retail sales, prices).

    Data is fetched from the EIA electricity route, by default the
    ``retail-sales/data`` endpoint which returns time-series rows (response.data
    array and response.total). Use the ``/data`` subpath to get actual data;
    without it the API returns dataset metadata only. Query parameters map to
    EIA facets and pagination. A valid ``EIA_API_KEY`` must be set in the
    environment or the API will return 403. EIA errors (e.g. 403, 500) are
    surfaced with the same status code.

    :param subpath: Optional EIA path under electricity (default ``retail-sales/data``).
    :param state_id: Optional state facet (e.g. ``CO`` for Colorado).
    :param sector_id: Optional sector facet (e.g. ``RES`` for residential).
    :param length: Optional maximum number of rows (EIA max 5000).
    :param offset: Optional number of rows to skip for pagination.
    :param manager: Injected EIA manager (from :func:`get_eia_manager`).
    :returns: Raw JSON response from the EIA API.
    :raises HTTPException: With status code from EIA (e.g. 403, 502) on request failure.
    """
    params: dict[str, Any] = {}
    if state_id is not None:
        params["facets[stateid][]"] = state_id
    if sector_id is not None:
        params["facets[sectorid][]"] = sector_id
    if length is not None:
        params["length"] = length
    if offset is not None:
        params["offset"] = offset
    try:
        return await manager.get_electricity(subpath=subpath or "retail-sales/data", **params)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e)) from e
