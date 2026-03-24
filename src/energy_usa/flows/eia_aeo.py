"""Prefect flow: fetch EIA AEO (Annual Energy Outlook) and upsert into ingest.eia_aeo.

Long-term US energy projections. aeo_year parameter selects the vintage (default: latest=2023).
Period stored as DATE (Jan 1 of projection year).
"""

import asyncio
from typing import Any

from prefect import flow, task
from prefect.logging import get_run_logger

from energy_usa.config import Settings
from energy_usa.db.retail_sales import get_connection
from energy_usa.db.aeo import upsert_aeo
from energy_usa.eia.manager import EIAManager
from energy_usa.flows.date_range import resolve_date_range

EIA_PAGE_LENGTH = 5000
EIA_AEO_COLUMNS = ["value"]
# Latest available AEO year; update as new vintages are released
EIA_AEO_DEFAULT_YEAR = "2023"


@task(name="fetch-eia-aeo")
async def fetch_eia_aeo(
    *,
    base_url: str, api_key: str, timeout: float,
    max_concurrent: int, max_retries: int, page_delay_seconds: float = 0.0,
    start: str, end: str,
    aeo_year: str = EIA_AEO_DEFAULT_YEAR,
) -> list[dict[str, Any]]:
    """Fetch EIA AEO data for the specified vintage year.

    :param aeo_year: AEO vintage (e.g. "2023"). Route: aeo/{aeo_year}/data.
    """
    logger = get_run_logger()
    manager = EIAManager(
        base_url=base_url, api_key=api_key, timeout=timeout,
        max_concurrent=max_concurrent, max_retries=max_retries,
    )
    try:
        all_data: list[dict[str, Any]] = []
        offset = 0
        path = f"aeo/{aeo_year}/data"
        start_year = start[:4] if start else ""
        end_year = end[:4] if end else ""
        while True:
            params: dict[str, Any] = {
                "length": EIA_PAGE_LENGTH, "offset": offset,
                "data[]": EIA_AEO_COLUMNS,
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
        logger.info("AEO %s fetch complete: total rows=%s", aeo_year, len(all_data))
        return all_data
    finally:
        await manager.aclose()


@task(name="upsert-aeo")
def upsert_aeo_task(database_url: str, rows: list[dict[str, Any]], aeo_year: str = EIA_AEO_DEFAULT_YEAR) -> int:
    conn = get_connection(database_url)
    try:
        return upsert_aeo(conn, rows, aeo_year=aeo_year)
    finally:
        conn.close()


@flow(name="ingest-eia-aeo", retries=2)
async def ingest_eia_aeo(
    date_start: str | None = None,
    date_end: str | None = None,
    aeo_year: str = EIA_AEO_DEFAULT_YEAR,
) -> int:
    """Fetch EIA Annual Energy Outlook projections and upsert into ingest.eia_aeo.

    :param date_start: Start projection year (YYYY-MM). Defaults to first projection year.
    :param date_end: End projection year (YYYY-MM). Defaults to last projection year.
    :param aeo_year: AEO vintage to ingest (e.g. "2023"). Defaults to latest.
    :returns: Total rows upserted.
    """
    logger = get_run_logger()
    settings = Settings()
    if not settings.eia_api_key:
        raise ValueError("EIA_API_KEY required")
    if not settings.effective_ingest_url:
        raise ValueError("INGEST_DATABASE_URL required")
    start, end = resolve_date_range(date_start, date_end)
    logger.info("Ingest AEO %s: start=%s end=%s", aeo_year, start, end)
    data = await fetch_eia_aeo(
        base_url=settings.eia_base_url, api_key=settings.eia_api_key,
        timeout=settings.eia_ingest_timeout_seconds,
        max_concurrent=settings.eia_max_concurrent_requests,
        max_retries=settings.eia_max_retries,
        page_delay_seconds=settings.eia_page_delay_seconds,
        start=start, end=end, aeo_year=aeo_year,
    )
    total = upsert_aeo_task(settings.effective_ingest_url, data, aeo_year=aeo_year)
    logger.info("Complete: rows_upserted=%s", total)
    return total
