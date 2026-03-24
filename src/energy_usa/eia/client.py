"""EIA API v2 client: route-level requests with facets and pagination.

This module provides a low-level HTTP client for the U.S. Energy Information
Administration (EIA) API v2. It builds URLs and query parameters (including
the required API key in the query string per EIA docs) but does not handle
retries or concurrency; that is done by the manager layer.
"""

from typing import Any

import httpx

# EIA API key must be in the URL (not headers) per official docs
EIA_DEFAULT_BASE = "https://api.eia.gov/v2"


class EIAClient:
    """Low-level HTTP client for EIA API v2.

    Builds request URLs and query parameters (facets, pagination, etc.) and
    performs GET requests. Does not implement retries or concurrency limits;
    use :class:`EIAManager` for that. Can use a shared :class:`httpx.AsyncClient`
    when provided by the manager, or create a one-off client per request.
    """

    def __init__(
        self,
        *,
        base_url: str = EIA_DEFAULT_BASE,
        api_key: str = "",
        timeout: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize the EIA client.

        :param base_url: EIA API v2 base URL (e.g. ``https://api.eia.gov/v2``).
        :param api_key: API key from EIA Open Data registration; added to every request.
        :param timeout: Request timeout in seconds.
        :param client: Optional shared async HTTP client; if omitted, each request uses a new client.
        """
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._client = client  # caller (manager) may inject shared client

    def _url(self, path: str, params: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        """Build the full request URL and query parameters.

        The API key is always included in the query dict when set. Callers
        pass optional params (e.g. facets, length, offset); these are merged
        with the key. Path should be a relative segment like ``electricity/retail-sales``.

        :param path: Relative path under the base URL (leading slash optional).
        :param params: Optional query parameters to merge (e.g. ``{"length": 100}``).
        :returns: A (url, query_dict) pair suitable for httpx get(url, params=query_dict).
        """
        url = f"{self.base_url}/{path.lstrip('/')}"
        q: dict[str, Any] = dict(params) if params else {}
        if self._api_key:
            q["api_key"] = self._api_key
        return url, q

    async def _request(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform a GET request to the EIA API and return the JSON body.

        Uses the shared :attr:`_client` when set (by the manager); otherwise
        creates a temporary async client for this request. Raises
        :exc:`httpx.HTTPStatusError` on non-2xx responses.

        :param path: Relative path (e.g. ``electricity/retail-sales``).
        :param params: Optional query parameters.
        :returns: Parsed JSON response body.
        :raises httpx.HTTPStatusError: When the response status is not 2xx.
        """
        url, q = self._url(path, params)
        if self._client is not None:
            r = await self._client.get(url, params=q, timeout=self._timeout)
        else:
            async with httpx.AsyncClient() as one_off:
                r = await one_off.get(url, params=q, timeout=self._timeout)
        r.raise_for_status()
        return r.json()

    # --- Route methods (one per EIA top-level route) ---

    async def get_electricity(
        self,
        subpath: str = "",
        **params: Any,
    ) -> dict[str, Any]:
        """Request data from the EIA electricity route.

        The path is ``electricity`` or ``electricity/{subpath}``. Common
        subpaths include ``retail-sales`` and ``retail-sales/data``. Pass
        facets and pagination via keyword arguments (e.g. ``length=100``,
        ``facets[stateid][]=CO``).

        :param subpath: Optional path segment (e.g. ``retail-sales/data``).
        :param params: Query parameters forwarded to the API (facets, length, offset, sort, etc.).
        :returns: JSON response from the EIA API.
        """
        path = "electricity"
        if subpath:
            path = f"{path}/{subpath.strip('/')}"
        return await self._request(path, params if params else None)

    async def get_natural_gas(
        self,
        subpath: str = "",
        **params: Any,
    ) -> dict[str, Any]:
        """Request data from the EIA natural-gas route.

        Path is ``natural-gas`` or ``natural-gas/{subpath}``. Use subpath and
        params to narrow by dataset, facets, and pagination.

        :param subpath: Optional path segment under natural-gas.
        :param params: Query parameters for the API.
        :returns: JSON response from the EIA API.
        """
        path = "natural-gas"
        if subpath:
            path = f"{path}/{subpath.strip('/')}"
        return await self._request(path, params if params else None)

    async def get_petroleum(
        self,
        subpath: str = "",
        **params: Any,
    ) -> dict[str, Any]:
        """Request data from the EIA petroleum route.

        Path is ``petroleum`` or ``petroleum/{subpath}``.

        :param subpath: Optional path segment under petroleum.
        :param params: Query parameters for the API.
        :returns: JSON response from the EIA API.
        """
        path = "petroleum"
        if subpath:
            path = f"{path}/{subpath.strip('/')}"
        return await self._request(path, params if params else None)

    async def get_coal(
        self,
        subpath: str = "",
        **params: Any,
    ) -> dict[str, Any]:
        """Request data from the EIA coal route.

        Path is ``coal`` or ``coal/{subpath}``.

        :param subpath: Optional path segment under coal.
        :param params: Query parameters for the API.
        :returns: JSON response from the EIA API.
        """
        path = "coal"
        if subpath:
            path = f"{path}/{subpath.strip('/')}"
        return await self._request(path, params if params else None)

    async def get_total_energy(
        self,
        subpath: str = "",
        **params: Any,
    ) -> dict[str, Any]:
        """Request data from the EIA total-energy route.

        Path is ``total-energy`` or ``total-energy/{subpath}``. This route
        provides integrated summaries across energy sources.

        :param subpath: Optional path segment under total-energy.
        :param params: Query parameters for the API.
        :returns: JSON response from the EIA API.
        """
        path = "total-energy"
        if subpath:
            path = f"{path}/{subpath.strip('/')}"
        return await self._request(path, params if params else None)

    async def get_route(
        self,
        path: str,
        **params: Any,
    ) -> dict[str, Any]:
        """Generic GET for any EIA v2 path.

        Use this for routes not covered by the typed helpers above (e.g.
        ``coal/aggregate-production/data``, ``seds/data``, ``aeo/2023/data``).

        :param path: Full relative path under the base URL (e.g. ``seds/data``).
        :param params: Query parameters forwarded to the API.
        :returns: JSON response from the EIA API.
        """
        return await self._request(path.lstrip("/"), params if params else None)
