"""Prefect flow: fetch EIA electric-power-operational-data and upsert into Postgres.

Source cadence: monthly. Period is stored as DATE (first day of month).
Runs on a monthly schedule (or on-demand). Paginates the EIA
electric-power-operational-data/data endpoint and upserts into eia_electric_power_operational.
Default date range is last calendar month; pass date_start/date_end for backfill.
Requires EIA_API_KEY and INGEST_DATABASE_URL.
"""

import asyncio
from typing import Any

from prefect import flow, task
from prefect.logging import get_run_logger

from energy_usa.config import Settings
from energy_usa.db.connection import get_connection
from energy_usa.db.ingest.eia.electric_power_operational import upsert_electric_power_operational
from energy_usa.clients.eia import EIAManager
from energy_usa.flows.date_range import resolve_date_range

EIA_PAGE_LENGTH = 5000

# Cadence label exposed for backfill chunking and run naming.
CADENCE = "monthly"

# Data columns to request; EIA returns generation (net generation, MWh).
EIA_ELECTRIC_POWER_OPERATIONAL_DATA_COLUMNS = ["generation"]


@task(name="fetch-eia-electric-power-operational")
async def fetch_eia_electric_power_operational(
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
    """Fetch EIA electric-power-operational-data for the given date range via pagination.

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
                "data[]": EIA_ELECTRIC_POWER_OPERATIONAL_DATA_COLUMNS,
                "start": start,
                "end": end,
            }
            resp = await manager.get_electricity(
                subpath="electric-power-operational-data/data",
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


@task(name="upsert-electric-power-operational")
def upsert_electric_power_operational_task(
    database_url: str,
    rows: list[dict[str, Any]],
) -> int:
    """Upsert EIA electric-power-operational rows into Postgres.

    :returns: Number of rows affected (inserted or updated).
    """
    logger = get_run_logger()
    if not rows:
        return 0
    conn = get_connection(database_url)
    try:
        return upsert_electric_power_operational(conn, rows)
    finally:
        conn.close()


def _run_name(**kwargs):
    return make_run_name("monthly", kwargs.get("date_start"), kwargs.get("date_end"))


@flow(
    name="ingest-eia-electric-power-operational",
    flow_run_name="{date_start} - {date_end}: monthly",
    retries=2,
    retry_delay_seconds=60,
    timeout_seconds=1800,
)
async def ingest_eia_electric_power_operational(
    date_start: str | None = None,
    date_end: str | None = None,
) -> int:
    """Fetch EIA electric-power-operational-data and upsert into Postgres.

    Default date range is last calendar month. Pass date_start/date_end (YYYY-MM)
    for backfill. Paginates with length=5000 and offset until no more rows.
    Idempotent via upsert on (period, stateid, sectorid, fueltypeid).

    :param date_start: Optional start period (YYYY-MM). Defaults to last month.
    :param date_end: Optional end period (YYYY-MM). Defaults to last month.
    :returns: Total number of rows upserted.
    """
    logger = get_run_logger()
    settings = Settings()
    if not settings.eia_api_key:
        raise ValueError("EIA_API_KEY is required for ingest_eia_electric_power_operational")
    if not settings.ingest_database_url:
        raise ValueError("INGEST_DATABASE_URL is required for ingest_eia_electric_power_operational")

    start, end = resolve_date_range(date_start, date_end)
    logger.info("Ingest date range: start=%s end=%s", start, end)

    data = await fetch_eia_electric_power_operational(
        base_url=settings.eia_base_url,
        api_key=settings.eia_api_key,
        timeout=settings.eia_ingest_timeout_seconds,
        max_concurrent=settings.eia_max_concurrent_requests,
        max_retries=settings.eia_max_retries,
        page_delay_seconds=settings.eia_page_delay_seconds,
        start=start,
        end=end,
    )
    total = upsert_electric_power_operational_task(settings.ingest_database_url, data)
    if total == 0:
        logger.warning(
            "No data returned for %s→%s — EIA may not have published yet",
            start, end,
        )
        return 0
    logger.info("Ingest complete: total rows upserted=%s", total)
    return total
