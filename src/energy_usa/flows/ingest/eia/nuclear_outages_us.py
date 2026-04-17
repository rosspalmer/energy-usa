"""Prefect flow: fetch EIA nuclear-outages/us-nuclear-outages and upsert.

Daily US-wide nuclear capacity and outages. Period stored as DATE.
"""

import asyncio
from typing import Any

from prefect import flow, task
from prefect.logging import get_run_logger

from energy_usa.config import Settings
from energy_usa.db.connection import get_connection
from energy_usa.db.ingest.eia.nuclear_outages_us import upsert_nuclear_outages_us
from energy_usa.clients.eia import EIAManager
from energy_usa.flows.date_range import resolve_date_range

EIA_PAGE_LENGTH = 5000

# Cadence label exposed for backfill chunking and run naming.
CADENCE = "daily"
EIA_NUCLEAR_OUTAGES_US_COLUMNS = ["capacity", "outage", "percentOutage"]
EIA_NUCLEAR_OUTAGES_US_PATH = "nuclear-outages/us-nuclear-outages/data"


@task(name="fetch-eia-nuclear-outages-us")
async def fetch_eia_nuclear_outages_us(
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
        while True:
            params: dict[str, Any] = {
                "length": EIA_PAGE_LENGTH, "offset": offset,
                "data[]": EIA_NUCLEAR_OUTAGES_US_COLUMNS,
                "start": start, "end": end,
            }
            resp = await manager.get_route(EIA_NUCLEAR_OUTAGES_US_PATH, **params)
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


@task(name="upsert-nuclear-outages-us")
def upsert_nuclear_outages_us_task(database_url: str, rows: list[dict[str, Any]]) -> int:
    conn = get_connection(database_url)
    try:
        return upsert_nuclear_outages_us(conn, rows)
    finally:
        conn.close()


def _run_name(**kwargs):
    return make_run_name("daily", kwargs.get("date_start"), kwargs.get("date_end"))


@flow(
    name="ingest-eia-nuclear-outages-us",
    flow_run_name="{date_start} - {date_end}: daily",
    retries=2,
    retry_delay_seconds=60,
    timeout_seconds=900,
)
async def ingest_eia_nuclear_outages_us(
    date_start: str | None = None, date_end: str | None = None,
) -> int:
    """Fetch EIA US nuclear outages and upsert into eia.nuclear_outages_us."""
    logger = get_run_logger()
    settings = Settings()
    if not settings.eia_api_key:
        raise ValueError("EIA_API_KEY required")
    if not settings.ingest_database_url:
        raise ValueError("INGEST_DATABASE_URL required")
    start, end = resolve_date_range(date_start, date_end)
    data = await fetch_eia_nuclear_outages_us(
        base_url=settings.eia_base_url, api_key=settings.eia_api_key,
        timeout=settings.eia_ingest_timeout_seconds,
        max_concurrent=settings.eia_max_concurrent_requests,
        max_retries=settings.eia_max_retries,
        page_delay_seconds=settings.eia_page_delay_seconds,
        start=start, end=end,
    )
    total = upsert_nuclear_outages_us_task(settings.ingest_database_url, data)
    if total == 0:
        logger.warning(
            "No data returned for %s→%s — EIA may not have published yet",
            start, end,
        )
        return 0
    logger.info("Complete: rows_upserted=%s", total)
    return total
