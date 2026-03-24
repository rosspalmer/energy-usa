"""Prefect flow: fetch EIA IEO (International Energy Outlook) and upsert into ingest.eia_ieo.

Long-term global energy projections by region. ieo_year parameter selects the vintage.
Period stored as DATE (Jan 1 of projection year).
"""

import asyncio
from typing import Any

from prefect import flow, task
from prefect.logging import get_run_logger

from energy_usa.config import Settings
from energy_usa.db.retail_sales import get_connection
from energy_usa.db.ieo import upsert_ieo
from energy_usa.eia.manager import EIAManager
from energy_usa.flows.date_range import resolve_date_range

EIA_PAGE_LENGTH = 5000
EIA_IEO_COLUMNS = ["value"]
EIA_IEO_DEFAULT_YEAR = "2023"


@task(name="fetch-eia-ieo")
async def fetch_eia_ieo(
    *,
    base_url: str, api_key: str, timeout: float,
    max_concurrent: int, max_retries: int, page_delay_seconds: float = 0.0,
    start: str, end: str,
    ieo_year: str = EIA_IEO_DEFAULT_YEAR,
) -> list[dict[str, Any]]:
    logger = get_run_logger()
    manager = EIAManager(
        base_url=base_url, api_key=api_key, timeout=timeout,
        max_concurrent=max_concurrent, max_retries=max_retries,
    )
    try:
        all_data: list[dict[str, Any]] = []
        offset = 0
        path = f"ieo/{ieo_year}/data"
        start_year = start[:4] if start else ""
        end_year = end[:4] if end else ""
        while True:
            params: dict[str, Any] = {
                "length": EIA_PAGE_LENGTH, "offset": offset,
                "data[]": EIA_IEO_COLUMNS,
                "start": start_year, "end": end_year,
            }
            resp = await manager.get_route(path, **params)
            response_body = resp.get("response") or {}
            data = response_body.get("data")
            if not isinstance(data, list):
                data = []
            if not data:
                break
            all_data.extend(data)
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
        logger.info("IEO %s fetch complete: total rows=%s", ieo_year, len(all_data))
        return all_data
    finally:
        await manager.aclose()


@task(name="upsert-ieo")
def upsert_ieo_task(database_url: str, rows: list[dict[str, Any]], ieo_year: str = EIA_IEO_DEFAULT_YEAR) -> int:
    conn = get_connection(database_url)
    try:
        return upsert_ieo(conn, rows, ieo_year=ieo_year)
    finally:
        conn.close()


@flow(name="ingest-eia-ieo", retries=2)
async def ingest_eia_ieo(
    date_start: str | None = None,
    date_end: str | None = None,
    ieo_year: str = EIA_IEO_DEFAULT_YEAR,
) -> int:
    """Fetch EIA International Energy Outlook projections and upsert into ingest.eia_ieo.

    :param ieo_year: IEO vintage (e.g. "2023"). Route: ieo/{ieo_year}/data.
    """
    logger = get_run_logger()
    settings = Settings()
    if not settings.eia_api_key:
        raise ValueError("EIA_API_KEY required")
    if not settings.effective_ingest_url:
        raise ValueError("INGEST_DATABASE_URL required")
    start, end = resolve_date_range(date_start, date_end)
    data = await fetch_eia_ieo(
        base_url=settings.eia_base_url, api_key=settings.eia_api_key,
        timeout=settings.eia_ingest_timeout_seconds,
        max_concurrent=settings.eia_max_concurrent_requests,
        max_retries=settings.eia_max_retries,
        page_delay_seconds=settings.eia_page_delay_seconds,
        start=start, end=end, ieo_year=ieo_year,
    )
    total = upsert_ieo_task(settings.effective_ingest_url, data, ieo_year=ieo_year)
    logger.info("Complete: rows_upserted=%s", total)
    return total
