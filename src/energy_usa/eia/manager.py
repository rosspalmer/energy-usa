"""EIA API call manager: concurrency limit, retries with backoff, and timeouts.

This module provides the single entry point for all outbound calls to the EIA API.
It wraps :class:`EIAClient` with a semaphore to limit concurrent requests, retries
on transient failures (5xx, timeouts, connection errors) with exponential backoff,
and applies a request timeout to every call. FastAPI endpoints should depend on
this manager rather than calling the EIA client directly.
"""

import asyncio
import logging
from typing import Any

import httpx

from energy_usa.eia.client import EIAClient

logger = logging.getLogger(__name__)


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

        The semaphore ensures at most ``max_concurrent`` requests run at once. On :exc:`httpx.HTTPStatusError` (5xx only),
        :exc:`httpx.TimeoutException`, or :exc:`httpx.ConnectError`, the call is
        retried after an exponential backoff (1s, 2s, 4s, ...) up to :attr:`_max_retries`
        attempts. Client errors (4xx) are not retried and are re-raised immediately.

        :param coro_factory: A callable that returns an awaitable (e.g. a coroutine).
        :returns: The result of the awaitable.
        :raises httpx.HTTPStatusError: On 4xx or after retries exhausted for 5xx/timeout/connect.
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
                if isinstance(e, httpx.HTTPStatusError) and e.response.status_code < 500:
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
