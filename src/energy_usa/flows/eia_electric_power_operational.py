"""Prefect flow: fetch EIA electric-power-operational-data and upsert into Postgres.

Runs on a monthly schedule (or on-demand). Paginates the EIA
electric-power-operational-data/data endpoint and upserts into eia_electric_power_operational.
Requires EIA_API_KEY and DATABASE_URL.
"""

from typing import Any

from prefect import flow, task
from prefect.logging import get_run_logger

from energy_usa.config import Settings
from energy_usa.db import get_connection, upsert_electric_power_operational
from energy_usa.eia.manager import EIAManager

EIA_PAGE_LENGTH = 5000

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
) -> list[dict[str, Any]]:
    """Fetch all EIA electric-power-operational-data via pagination.

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
                    total_n = int(total_available)
                except (TypeError, ValueError):
                    total_n = None
                if total_n is not None and offset >= total_n:
                    break
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


@flow(name="ingest-eia-electric-power-operational", retries=2)
async def ingest_eia_electric_power_operational() -> int:
    """Fetch all EIA electric-power-operational-data and upsert into Postgres.

    Paginates with length=5000 and offset until no more rows. Idempotent via
    upsert on (period, stateid, sectorid, fueltypeid).

    :returns: Total number of rows upserted.
    """
    logger = get_run_logger()
    settings = Settings()
    if not settings.eia_api_key:
        raise ValueError("EIA_API_KEY is required for ingest_eia_electric_power_operational")
    if not settings.database_url:
        raise ValueError("DATABASE_URL is required for ingest_eia_electric_power_operational")

    data = await fetch_eia_electric_power_operational(
        base_url=settings.eia_base_url,
        api_key=settings.eia_api_key,
        timeout=settings.eia_request_timeout_seconds,
        max_concurrent=settings.eia_max_concurrent_requests,
        max_retries=settings.eia_max_retries,
    )
    total = upsert_electric_power_operational_task(settings.database_url, data)
    logger.info("Ingest complete: total rows upserted=%s", total)
    return total
