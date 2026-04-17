"""Prefect flow: fetch EIA International and upsert into eia.international.

Annual international energy data by country, product, and activity. Period stored as DATE (Jan 1).
"""

import asyncio
from typing import Any

from prefect import flow, task
from prefect.logging import get_run_logger

from energy_usa.config import Settings
from energy_usa.db.connection import get_connection
from energy_usa.db.ingest.eia.international import upsert_international
from energy_usa.clients.eia import EIAManager
from energy_usa.flows.date_range import resolve_date_range

EIA_PAGE_LENGTH = 5000

# Cadence label exposed for backfill chunking and run naming.
CADENCE = "annual"
EIA_INTERNATIONAL_COLUMNS = ["value"]
EIA_INTERNATIONAL_PATH = "international/data"


@task(name="fetch-eia-international")
async def fetch_eia_international(
    *,
    base_url: str, api_key: str, timeout: float,
    max_concurrent: int, max_retries: int, page_delay_seconds: float = 0.0,
    start: str, end: str,
) -> list[dict[str, Any]]:
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
                "data[]": EIA_INTERNATIONAL_COLUMNS,
                "frequency": "annual", "start": start_year, "end": end_year,
            }
            resp = await manager.get_route(EIA_INTERNATIONAL_PATH, **params)
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
                    logger.warning(
                        "Unexpected 'total' value from EIA API: %r — skipping pagination check",
                        total_available,
                    )
            if page_delay_seconds > 0:
                await asyncio.sleep(page_delay_seconds)
        logger.info("Fetch complete: total rows=%s", len(all_data))
        return all_data
    finally:
        await manager.aclose()


@task(name="upsert-international")
def upsert_international_task(database_url: str, rows: list[dict[str, Any]]) -> int:
    conn = get_connection(database_url)
    try:
        return upsert_international(conn, rows)
    finally:
        conn.close()


def _run_name(**kwargs):
    return make_run_name("annual", kwargs.get("date_start"), kwargs.get("date_end"))


@flow(
    name="ingest-eia-international",
    flow_run_name="{date_start} - {date_end}: annual",
    retries=2,
    retry_delay_seconds=60,
    timeout_seconds=3600,
)
async def ingest_eia_international(
    date_start: str | None = None, date_end: str | None = None,
) -> int:
    """Fetch EIA international energy data and upsert into eia.international.

    Very large dataset — use narrow year windows and expect many pages.
    """
    logger = get_run_logger()
    settings = Settings()
    if not settings.eia_api_key:
        raise ValueError("EIA_API_KEY required")
    if not settings.ingest_database_url:
        raise ValueError("INGEST_DATABASE_URL required")
    start, end = resolve_date_range(date_start, date_end)
    data = await fetch_eia_international(
        base_url=settings.eia_base_url, api_key=settings.eia_api_key,
        timeout=settings.eia_ingest_timeout_seconds,
        max_concurrent=settings.eia_max_concurrent_requests,
        max_retries=settings.eia_max_retries,
        page_delay_seconds=settings.eia_page_delay_seconds,
        start=start, end=end,
    )
    total = upsert_international_task(settings.ingest_database_url, data)
    if total == 0:
        logger.warning(
            "No data returned for %s→%s — EIA may not have published yet",
            start, end,
        )
        return 0
    logger.info("Complete: rows_upserted=%s", total)
    return total
