"""Prefect flow: fetch EIA electric-power-operational-data and upsert into Postgres.

Runs on a monthly schedule (or on-demand). Paginates the EIA
electric-power-operational-data/data endpoint and upserts into eia_electric_power_operational.
Default date range is last calendar month; pass date_start/date_end for backfill.
Requires EIA_API_KEY and DATABASE_URL.
"""

import asyncio
import json
import time
from typing import Any

from prefect import flow, task
from prefect.logging import get_run_logger

from energy_usa.config import Settings
from energy_usa.db import get_connection, upsert_electric_power_operational
from energy_usa.eia.manager import EIAManager
from energy_usa.flows.date_range import resolve_date_range

EIA_PAGE_LENGTH = 5000
DEBUG_LOG_PATH = "/Users/rpalmer/repo/energy-usa/.cursor/debug-c40a77.log"
DEBUG_SESSION_ID = "c40a77"

# Data columns to request; EIA returns generation (net generation, MWh).
EIA_ELECTRIC_POWER_OPERATIONAL_DATA_COLUMNS = ["generation"]


def _agent_debug_log(
    *,
    run_id: str,
    hypothesis_id: str,
    location: str,
    message: str,
    data: dict[str, Any],
) -> None:
    try:
        payload = {
            "sessionId": DEBUG_SESSION_ID,
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        pass


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
    run_id = f"electric_power_operational:{start}->{end}"
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
            if offset == 0:
                first_row_keys = list(data[0].keys()) if data and isinstance(data[0], dict) else None
                # region agent log
                _agent_debug_log(
                    run_id=run_id,
                    hypothesis_id="H1,H5",
                    location="eia_electric_power_operational.py:fetch_page_0",
                    message="First page response shape",
                    data={
                        "params": params,
                        "resp_keys": list(resp.keys()),
                        "response_keys": list(response_body.keys()) if isinstance(response_body, dict) else [],
                        "data_len": len(data),
                        "first_row_keys": first_row_keys,
                        "total": response_body.get("total"),
                    },
                )
                # endregion
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
        # region agent log
        _agent_debug_log(
            run_id=run_id,
            hypothesis_id="H1",
            location="eia_electric_power_operational.py:fetch_complete",
            message="Fetch complete",
            data={"total_rows": len(all_data), "start": start, "end": end},
        )
        # endregion
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
    if not settings.database_url:
        raise ValueError("DATABASE_URL is required for ingest_eia_electric_power_operational")

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
    total = upsert_electric_power_operational_task(settings.database_url, data)
    logger.info("Ingest complete: total rows upserted=%s", total)
    return total
