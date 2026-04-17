"""EIA API v2 client: route-level requests with facets and pagination.

This module provides a low-level HTTP client for the U.S. Energy Information
Administration (EIA) API v2. It builds URLs and query parameters (including
the required API key in the query string per EIA docs) but does not handle
retries or concurrency; that is done by the manager layer.
"""

import asyncio
import logging
from typing import Any

import httpx

# EIA API key must be in the URL (not headers) per official docs
EIA_DEFAULT_BASE = "https://api.eia.gov/v2"

logger = logging.getLogger(__name__)


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


class EIAManager:
    """Central manager for all EIA API access with concurrency and retry behavior.

    One instance is created at application startup and stored in ``app.state.eia_manager``.
    It holds a shared :class:`httpx.AsyncClient` and an :class:`EIAClient` that uses it.
    All requests are rate-limited by a semaphore, retried on 5xx/timeouts/connection
    errors with exponential backoff, and subject to a per-request timeout. Client
    errors (e.g. 403 for missing API key) are not retried.
    """

    def __init__(
        self,
        *,
        base_url: str = "https://api.eia.gov/v2",
        api_key: str = "",
        timeout: float = 30.0,
        max_concurrent: int = 4,
        max_retries: int = 3,
    ) -> None:
        """Initialize the EIA manager and its internal client.

        :param base_url: EIA API v2 base URL.
        :param api_key: EIA API key for authentication.
        :param timeout: Request timeout in seconds for each HTTP call.
        :param max_concurrent: Maximum number of in-flight EIA requests (semaphore size).
        :param max_retries: Number of retry attempts for retryable failures.
        """
        self._timeout = timeout
        self._max_retries = max_retries
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._client = httpx.AsyncClient(timeout=timeout)
        self._eia_client = EIAClient(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            client=self._client,
        )

    async def aclose(self) -> None:
        """Close the shared HTTP client and release connections.

        Call this during application shutdown (e.g. in the FastAPI lifespan)
        to avoid leaving connections open. After calling, the manager must
        not be used for further requests.
        """
        await self._client.aclose()

    async def _with_retry(self, coro_factory: Any) -> Any:
        """Run a coroutine produced by the factory with retries and concurrency limit.

        The semaphore ensures at most ``max_concurrent`` requests run at once.
        Retries with exponential backoff on:

        * :exc:`httpx.TimeoutException` and :exc:`httpx.ConnectError` (transient
          network conditions),
        * :exc:`httpx.HTTPStatusError` with status >= 500 (server-side
          failures),
        * :exc:`httpx.HTTPStatusError` with status 429 (rate-limited; the API
          is asking us to slow down — uses a longer backoff).

        Other 4xx errors are not retried and are re-raised immediately.

        :param coro_factory: A callable that returns an awaitable (e.g. a coroutine).
        :returns: The result of the awaitable.
        :raises httpx.HTTPStatusError: On non-retryable 4xx or after retries
            exhausted for 5xx/429/timeout/connect.
        """
        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                async with self._semaphore:
                    return await coro_factory()
            except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError) as e:
                last_exc = e
                if attempt == self._max_retries - 1:
                    raise
                # 4xx is generally a permanent client error — but 429 means
                # "slow down", so retry it with a longer backoff.
                if isinstance(e, httpx.HTTPStatusError):
                    status = e.response.status_code
                    if status == 429:
                        # Honor a Retry-After header if present, else back off
                        # more aggressively than the default exponential.
                        retry_after = e.response.headers.get("retry-after")
                        try:
                            delay = float(retry_after) if retry_after else 5.0 * (2**attempt)
                        except ValueError:
                            delay = 5.0 * (2**attempt)
                        logger.warning(
                            "EIA rate-limited (429), backing off %.1fs (attempt %s/%s)",
                            delay, attempt + 1, self._max_retries,
                        )
                        await asyncio.sleep(delay)
                        continue
                    if status < 500:
                        raise
                delay = 2**attempt
                logger.warning("EIA request failed (attempt %s/%s), retrying in %ss: %s", attempt + 1, self._max_retries, delay, e)
                await asyncio.sleep(delay)
        raise last_exc  # type: ignore[misc]

    # --- Passthrough to EIAClient with retry + concurrency ---

    async def get_electricity(self, subpath: str = "", **params: Any) -> dict[str, Any]:
        """Fetch electricity data from EIA with retry and concurrency limits.

        :param subpath: Optional path under electricity (e.g. ``retail-sales``).
        :param params: Query parameters (facets, length, offset, etc.).
        :returns: EIA API JSON response.
        """
        return await self._with_retry(lambda: self._eia_client.get_electricity(subpath=subpath, **params))

    async def get_natural_gas(self, subpath: str = "", **params: Any) -> dict[str, Any]:
        """Fetch natural gas data from EIA with retry and concurrency limits.

        :param subpath: Optional path under natural-gas.
        :param params: Query parameters.
        :returns: EIA API JSON response.
        """
        return await self._with_retry(lambda: self._eia_client.get_natural_gas(subpath=subpath, **params))

    async def get_petroleum(self, subpath: str = "", **params: Any) -> dict[str, Any]:
        """Fetch petroleum data from EIA with retry and concurrency limits.

        :param subpath: Optional path under petroleum.
        :param params: Query parameters.
        :returns: EIA API JSON response.
        """
        return await self._with_retry(lambda: self._eia_client.get_petroleum(subpath=subpath, **params))

    async def get_coal(self, subpath: str = "", **params: Any) -> dict[str, Any]:
        """Fetch coal data from EIA with retry and concurrency limits.

        :param subpath: Optional path under coal.
        :param params: Query parameters.
        :returns: EIA API JSON response.
        """
        return await self._with_retry(lambda: self._eia_client.get_coal(subpath=subpath, **params))

    async def get_total_energy(self, subpath: str = "", **params: Any) -> dict[str, Any]:
        """Fetch total-energy data from EIA with retry and concurrency limits.

        :param subpath: Optional path under total-energy.
        :param params: Query parameters.
        :returns: EIA API JSON response.
        """
        return await self._with_retry(lambda: self._eia_client.get_total_energy(subpath=subpath, **params))

    async def get_route(self, path: str, **params: Any) -> dict[str, Any]:
        """Fetch any EIA v2 path with retry and concurrency limits.

        Use this for routes not covered by the typed helpers (e.g. ``seds/data``,
        ``coal/aggregate-production/data``, ``aeo/2023/data``).

        :param path: Full relative path under the base URL.
        :param params: Query parameters.
        :returns: EIA API JSON response.
        """
        return await self._with_retry(lambda: self._eia_client.get_route(path, **params))
