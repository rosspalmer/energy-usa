"""Prefect flow: fetch EIA coal/consumption-and-quality and upsert.

Quarterly coal consumption with quality metrics. Period stored as TEXT.
"""

import asyncio
from typing import Any

from prefect import flow, task
from prefect.logging import get_run_logger

from energy_usa.config import Settings
from energy_usa.db.connection import get_connection
from energy_usa.db.ingest.eia.coal_consumption_quality import upsert_coal_consumption_quality
from energy_usa.clients.eia import EIAManager
from energy_usa.flows.date_range import resolve_date_range

EIA_PAGE_LENGTH = 5000

# Cadence label exposed for backfill chunking and run naming.
CADENCE = "quarterly"
EIA_COAL_CONS_QUALITY_COLUMNS = ["consumption", "heat-content", "sulfur-content", "ash-content"]
EIA_COAL_CONS_QUALITY_PATH = "coal/consumption-and-quality/data"


@task(name="fetch-eia-coal-consumption-quality")
async def fetch_eia_coal_consumption_quality(
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
                "data[]": EIA_COAL_CONS_QUALITY_COLUMNS,
                "start": start[:4], "end": end[:4],
            }
            resp = await manager.get_route(EIA_COAL_CONS_QUALITY_PATH, **params)
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


@task(name="upsert-coal-consumption-quality")
def upsert_coal_consumption_quality_task(database_url: str, rows: list[dict[str, Any]]) -> int:
    conn = get_connection(database_url)
    try:
        return upsert_coal_consumption_quality(conn, rows)
    finally:
        conn.close()


def _run_name(**kwargs):
    return make_run_name("quarterly", kwargs.get("date_start"), kwargs.get("date_end"))


@flow(
    name="ingest-eia-coal-consumption-quality",
    flow_run_name="{date_start} - {date_end}: quarterly",
    retries=2,
    retry_delay_seconds=60,
    timeout_seconds=1800,
)
async def ingest_eia_coal_consumption_quality(
    date_start: str | None = None, date_end: str | None = None,
) -> int:
    """Fetch EIA coal consumption/quality and upsert into eia.coal_consumption_quality."""
    logger = get_run_logger()
    settings = Settings()
    if not settings.eia_api_key:
        raise ValueError("EIA_API_KEY required")
    if not settings.ingest_database_url:
        raise ValueError("INGEST_DATABASE_URL required")
    start, end = resolve_date_range(date_start, date_end)
    data = await fetch_eia_coal_consumption_quality(
        base_url=settings.eia_base_url, api_key=settings.eia_api_key,
        timeout=settings.eia_ingest_timeout_seconds,
        max_concurrent=settings.eia_max_concurrent_requests,
        max_retries=settings.eia_max_retries,
        page_delay_seconds=settings.eia_page_delay_seconds,
        start=start, end=end,
    )
    total = upsert_coal_consumption_quality_task(settings.ingest_database_url, data)
    if total == 0:
        logger.warning(
            "No data returned for %s→%s — EIA may not have published yet",
            start, end,
        )
        return 0
    logger.info("Complete: rows_upserted=%s", total)
    return total
