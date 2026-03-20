"""Prefect flow: fetch EIA state-electricity-profiles source-disposition and upsert into Postgres.

Source cadence: monthly. Period is stored as DATE (first day of month).
Runs on a monthly schedule (or on-demand). Paginates the EIA
state-electricity-profiles/source-disposition/data endpoint and upserts into
eia_state_source_disposition. Default date range is last calendar month;
pass date_start/date_end for backfill. Requires EIA_API_KEY and DATABASE_URL.
"""

import asyncio
from typing import Any

from prefect import flow, task
from prefect.logging import get_run_logger

from energy_usa.config import Settings
from energy_usa.db import get_connection, upsert_state_source_disposition
from energy_usa.eia.manager import EIAManager
from energy_usa.flows.date_range import resolve_date_range

EIA_PAGE_LENGTH = 5000

# Data columns to request; EIA returns hyphenated keys.
EIA_SOURCE_DISPOSITION_DATA_COLUMNS = ["net-interstate-trade", "total-disposition"]


@task(name="fetch-eia-state-source-disposition")
async def fetch_eia_state_source_disposition(
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
    """Fetch EIA state-electricity-profiles source-disposition data for the given date range via pagination.

    :param start: Start period (YYYY-MM) for EIA API.
    :param end: End period (YYYY-MM) for EIA API.
    :returns: Combined list of row dicts from all pages.
    """
    logger = get_run_logger()
    manager = EIAManager(
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
        max_concurrent=max_concurrent,
        max_retries=max_retries,
    )
    try:
        all_data: list[dict[str, Any]] = []
        offset = 0
        while True:
            params: dict[str, Any] = {
                "length": EIA_PAGE_LENGTH,
                "offset": offset,
                "data[]": EIA_SOURCE_DISPOSITION_DATA_COLUMNS,
                "start": start,
                "end": end,
            }
            resp = await manager.get_electricity(
                subpath="state-electricity-profiles/source-disposition/data",
                **params,
            )
            response_body = resp.get("response") or {}
            data = response_body.get("data")
            if not isinstance(data, list):
                data = []
            if not data:
                break
            all_data.extend(data)
            logger.info("Fetched page: offset=%s, rows=%s", offset, len(data))
            offset += len(data)
            total_available = response_body.get("total")
            if total_available is not None:
                try:
                    total_n = int(total_available)
                except (TypeError, ValueError):
                    total_n = None
                if total_n is not None and offset >= total_n:
                    break
            if page_delay_seconds > 0:
                await asyncio.sleep(page_delay_seconds)
        logger.info("Fetch complete: total rows=%s", len(all_data))
        return all_data
    finally:
        await manager.aclose()


@task(name="upsert-state-source-disposition")
def upsert_state_source_disposition_task(
    database_url: str,
    rows: list[dict[str, Any]],
) -> int:
    """Upsert EIA source-disposition rows into Postgres.

    :returns: Number of rows affected (inserted or updated).
    """
    logger = get_run_logger()
    if not rows:
        return 0
    conn = get_connection(database_url)
    try:
        return upsert_state_source_disposition(conn, rows)
    finally:
        conn.close()


@flow(name="ingest-eia-state-source-disposition", retries=2)
async def ingest_eia_state_source_disposition(
    date_start: str | None = None,
    date_end: str | None = None,
) -> int:
    """Fetch EIA state source-disposition data and upsert into Postgres.

    Default date range is last calendar month. Pass date_start/date_end (YYYY-MM)
    for backfill. Paginates with length=5000 and offset until no more rows.
    Idempotent via upsert on (period, stateid).

    :param date_start: Optional start period (YYYY-MM). Defaults to last month.
    :param date_end: Optional end period (YYYY-MM). Defaults to last month.
    :returns: Total number of rows upserted.
    """
    logger = get_run_logger()
    settings = Settings()
    if not settings.eia_api_key:
        raise ValueError("EIA_API_KEY is required for ingest_eia_state_source_disposition")
    if not settings.effective_ingest_url:
        raise ValueError("INGEST_DATABASE_URL (or DATABASE_URL) is required for ingest_eia_state_source_disposition")

    start, end = resolve_date_range(date_start, date_end)
    logger.info("Ingest date range: start=%s end=%s", start, end)

    data = await fetch_eia_state_source_disposition(
        base_url=settings.eia_base_url,
        api_key=settings.eia_api_key,
        timeout=settings.eia_ingest_timeout_seconds,
        max_concurrent=settings.eia_max_concurrent_requests,
        max_retries=settings.eia_max_retries,
        page_delay_seconds=settings.eia_page_delay_seconds,
        start=start,
        end=end,
    )
    total = upsert_state_source_disposition_task(settings.effective_ingest_url, data)
    logger.info("Ingest complete: total rows upserted=%s", total)
    return total
