"""Prefect flow: fetch EIA electricity/facility-fuel and upsert into ingest.eia_facility_fuel.

Annual generation and fuel consumption per plant. Period stored as DATE (Jan 1 of year).
Large dataset — use narrow date ranges or add facet filters for state via date_start/date_end year range.
"""

import asyncio
from typing import Any

from prefect import flow, task
from prefect.logging import get_run_logger

from energy_usa.config import Settings
from energy_usa.db.retail_sales import get_connection
from energy_usa.db.facility_fuel import upsert_facility_fuel
from energy_usa.eia.manager import EIAManager
from energy_usa.flows.date_range import resolve_date_range

EIA_PAGE_LENGTH = 5000
EIA_FACILITY_FUEL_COLUMNS = ["generation", "consumption-ej", "consumption-mmbtus"]


@task(name="fetch-eia-facility-fuel")
async def fetch_eia_facility_fuel(
    *,
    base_url: str,
    api_key: str,
    timeout: float,
    max_concurrent: int,
    max_retries: int,
    page_delay_seconds: float = 0.0,
    start: str,
    end: str,
) -> list[dict[str, Any]]:
    """Fetch EIA facility-fuel data for the given year range.

    :param start: Start year (YYYY or YYYY-MM).
    :param end: End year (YYYY or YYYY-MM).
    :returns: Combined list of row dicts from all pages.
    """
    logger = get_run_logger()
    manager = EIAManager(
        base_url=base_url, api_key=api_key, timeout=timeout,
        max_concurrent=max_concurrent, max_retries=max_retries,
    )
    try:
        all_data: list[dict[str, Any]] = []
        offset = 0
        start_year = start[:4] if start else ""
        end_year = end[:4] if end else ""
        while True:
            params: dict[str, Any] = {
                "length": EIA_PAGE_LENGTH, "offset": offset,
                "data[]": EIA_FACILITY_FUEL_COLUMNS,
                "frequency": "annual",
                "start": start_year,
                "end": end_year,
            }
            resp = await manager.get_electricity(subpath="facility-fuel/data", **params)
            response_body = resp.get("response") or {}
            data = response_body.get("data")
            if not isinstance(data, list):
                data = []
            if not data:
                break
            all_data.extend(data)
            logger.info("Fetched page: offset=%s rows=%s", offset, len(data))
            offset += len(data)
            total_available = response_body.get("total")
            if total_available is not None:
                try:
                    if offset >= int(total_available):
                        break
                except (TypeError, ValueError):
                    pass
            if page_delay_seconds > 0:
                await asyncio.sleep(page_delay_seconds)
        logger.info("Fetch complete: total rows=%s", len(all_data))
        return all_data
    finally:
        await manager.aclose()


@task(name="upsert-facility-fuel")
def upsert_facility_fuel_task(database_url: str, rows: list[dict[str, Any]]) -> int:
    conn = get_connection(database_url)
    try:
        return upsert_facility_fuel(conn, rows)
    finally:
        conn.close()


@flow(name="ingest-eia-facility-fuel", retries=2)
async def ingest_eia_facility_fuel(
    date_start: str | None = None,
    date_end: str | None = None,
) -> int:
    """Fetch EIA facility-fuel annual data and upsert into ingest.eia_facility_fuel.

    Source cadence: annual. Expect large volumes — use narrow year ranges.
    :param date_start: Start year/month (YYYY-MM). Defaults to last month.
    :param date_end: End year/month (YYYY-MM). Defaults to last month.
    :returns: Total rows upserted.
    """
    logger = get_run_logger()
    settings = Settings()
    if not settings.eia_api_key:
        raise ValueError("EIA_API_KEY required")
    if not settings.effective_ingest_url:
        raise ValueError("INGEST_DATABASE_URL required")
    start, end = resolve_date_range(date_start, date_end)
    logger.info("Ingest (annual): start=%s end=%s", start, end)
    data = await fetch_eia_facility_fuel(
        base_url=settings.eia_base_url, api_key=settings.eia_api_key,
        timeout=settings.eia_ingest_timeout_seconds,
        max_concurrent=settings.eia_max_concurrent_requests,
        max_retries=settings.eia_max_retries,
        page_delay_seconds=settings.eia_page_delay_seconds,
        start=start, end=end,
    )
    total = upsert_facility_fuel_task(settings.effective_ingest_url, data)
    logger.info("Complete: rows_upserted=%s", total)
    return total
