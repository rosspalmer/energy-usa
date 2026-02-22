"""Prefect flow: fetch EIA electricity retail-sales data and upsert into Postgres.

Runs on a monthly schedule (or on-demand). Paginates the EIA retail-sales/data
endpoint and upserts into eia_retail_sales. Requires EIA_API_KEY and DATABASE_URL.
"""

import asyncio
import logging
from typing import Any

from prefect import flow

from energy_usa.config import Settings
from energy_usa.db import get_connection, upsert_retail_sales
from energy_usa.eia.manager import EIAManager

logger = logging.getLogger(__name__)

EIA_PAGE_LENGTH = 5000


@flow(name="ingest-eia-retail-sales", retries=2)
async def ingest_eia_retail_sales() -> int:
    """Fetch all EIA electricity retail-sales data and upsert into Postgres.

    Paginates with length=5000 and offset until no more rows. Uses
    retail-sales/data for time-series rows. Idempotent via upsert on
    (period, stateid, sectorid).

    :returns: Total number of rows upserted.
    """
    settings = Settings()
    if not settings.eia_api_key:
        raise ValueError("EIA_API_KEY is required for ingest_eia_retail_sales")
    if not settings.database_url:
        raise ValueError("DATABASE_URL is required for ingest_eia_retail_sales")

    manager = EIAManager(
        base_url=settings.eia_base_url,
        api_key=settings.eia_api_key,
        timeout=settings.eia_request_timeout_seconds,
        max_concurrent=settings.eia_max_concurrent_requests,
        max_retries=settings.eia_max_retries,
    )
    try:
        conn = get_connection(settings.database_url)
        try:
            total_upserted = 0
            offset = 0
            while True:
                params: dict[str, Any] = {"length": EIA_PAGE_LENGTH, "offset": offset}
                resp = await manager.get_electricity(
                    subpath="retail-sales/data",
                    **params,
                )
                response_body = resp.get("response") or {}
                data = response_body.get("data")
                if not isinstance(data, list):
                    data = []
                if not data:
                    break
                # Run sync upsert in thread pool to avoid blocking
                n = await asyncio.to_thread(upsert_retail_sales, conn, data)
                total_upserted += n
                logger.info("Upserted page: offset=%s, rows=%s", offset, n)
                offset += len(data)
                total_available = response_body.get("total")
                if total_available is not None and offset >= total_available:
                    break
            logger.info("Ingest complete: total rows upserted=%s", total_upserted)
            return total_upserted
        finally:
            conn.close()
    finally:
        await manager.aclose()
