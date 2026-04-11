"""Protocol defining the interface for data source API clients."""

from typing import Any, Protocol


class DataClient(Protocol):
    """Interface that all source API clients must satisfy.

    :param dataset: Dataset identifier (e.g. 'retail-sales/data').
    :param start: Start period (YYYY-MM or YYYY).
    :param end: End period (YYYY-MM or YYYY).
    :param columns: Data columns to request.
    :returns: List of row dicts from the API.
    """

    async def fetch_dataset(
        self, dataset: str, start: str, end: str, columns: list[str]
    ) -> list[dict[str, Any]]: ...

    async def aclose(self) -> None: ...
