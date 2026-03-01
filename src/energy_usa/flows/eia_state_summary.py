"""Prefect flow: fetch EIA state-electricity-profiles summary and upsert into Postgres.

Runs on a monthly schedule (or on-demand). Paginates the EIA
state-electricity-profiles/summary/data endpoint and upserts into eia_state_summary.
Default date range is last calendar month; pass date_start/date_end for backfill.
Requires EIA_API_KEY and DATABASE_URL.
"""

import asyncio
from typing import Any

from prefect import flow, task
from prefect.logging import get_run_logger

from energy_usa.config import Settings
from energy_usa.db import get_connection, upsert_state_summary
from energy_usa.eia.manager import EIAManager
from energy_usa.flows.date_range import resolve_date_range

EIA_PAGE_LENGTH = 5000

# State-electricity-profiles/summary/data returns 400 if data[] is sent; request
# all columns by omitting data[] and map the keys we need in the DB layer.
# Expected keys in response: period, stateid, average-retail-price, total-generation, total-consumption (or equivalents).
# This dataset is annual-only per EIA; we request frequency=annual and convert date range to years.


@task(name="fetch-eia-state-summary")
async def fetch_eia_state_summary(
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
    """Fetch EIA state-electricity-profiles summary data for the given date range via pagination.

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
                "frequency": "annual",
                "start": start,
                "end": end,
            }
            resp = await manager.get_electricity(
                subpath="state-electricity-profiles/summary/data",
                **params,
            )
            # EIA may wrap in "response" or return data/total at top level
            response_body = resp.get("response") if "response" in resp else resp
            response_body = response_body or {}
            data = response_body.get("data")
            if not isinstance(data, list):
                data = []
            if offset == 0:
                logger.info(
                    "EIA state-summary first page: data_len=%s total=%s",
                    len(data),
                    response_body.get("total"),
                )
            if not data:
                break
            # If API returns rows as arrays, convert using response columns (EIA v2 variant)
            columns = response_body.get("columns")
            if columns and isinstance(columns, list) and data and isinstance(data[0], (list, tuple)):
                col_list = [c if isinstance(c, str) else str(c) for c in columns]
                for row in data:
                    if isinstance(row, (list, tuple)) and len(row) == len(col_list):
                        all_data.append(dict(zip(col_list, row)))
                    else:
                        all_data.append({})
            else:
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


@task(name="upsert-state-summary")
def upsert_state_summary_task(
    database_url: str,
    rows: list[dict[str, Any]],
) -> int:
    """Upsert EIA state summary rows into Postgres.

    :returns: Number of rows affected (inserted or updated).
    """
    logger = get_run_logger()
    if not rows:
        return 0
    # Log first row shape so we can see EIA's actual keys if upsert is 0
    first = rows[0]
    if isinstance(first, dict):
        logger.info("First row keys: %s", list(first.keys()))
    else:
        logger.info("First row type: %s (len=%s)", type(first).__name__, len(first) if hasattr(first, "__len__") else "?")
    conn = get_connection(database_url)
    try:
        return upsert_state_summary(conn, rows)
    finally:
        conn.close()


@flow(name="ingest-eia-state-summary", retries=2)
async def ingest_eia_state_summary(
    date_start: str | None = None,
    date_end: str | None = None,
) -> int:
    """Fetch EIA state-electricity-profiles summary data and upsert into Postgres.

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
        raise ValueError("EIA_API_KEY is required for ingest_eia_state_summary")
    if not settings.database_url:
        raise ValueError("DATABASE_URL is required for ingest_eia_state_summary")

    start, end = resolve_date_range(date_start, date_end)
    # State-electricity-profiles/summary is annual-only: use year range for API
    start_year = start[:4] if start else ""
    end_year = end[:4] if end else ""
    logger.info("Ingest date range: start=%s end=%s (API years: %s–%s)", start, end, start_year, end_year)

    data = await fetch_eia_state_summary(
        base_url=settings.eia_base_url,
        api_key=settings.eia_api_key,
        timeout=settings.eia_ingest_timeout_seconds,
        max_concurrent=settings.eia_max_concurrent_requests,
        max_retries=settings.eia_max_retries,
        page_delay_seconds=settings.eia_page_delay_seconds,
        start=start_year,
        end=end_year,
    )
    total = upsert_state_summary_task(settings.database_url, data)
    logger.info("Ingest complete: total rows upserted=%s", total)
    return total
