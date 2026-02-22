"""Prefect flow: run all EIA electricity dataset ingests as deployment runs.

Submits each ingest as a separate deployment run so the work pool can assign
them to different workers. Waits for all to complete and returns a summary.
Requires PREFECT_API_URL and deployments to be registered.
"""

import asyncio
from typing import Any

from prefect import flow
from prefect.deployments import run_deployment
from prefect.flow_runs import wait_for_flow_run
from prefect.logging import get_run_logger

from energy_usa.config import Settings

# Deployment names: "flow-name/deployment-name" (same in our deploy script)
DEPLOYMENT_NAMES = [
    "ingest-eia-retail-sales/ingest-eia-retail-sales",
    "ingest-eia-electric-power-operational/ingest-eia-electric-power-operational",
    "ingest-eia-state-source-disposition/ingest-eia-state-source-disposition",
    "ingest-eia-state-summary/ingest-eia-state-summary",
]


def _result_from_flow_run(flow_run: Any) -> int:
    """Return the flow run result (rows upserted) or 0 if failed."""
    if flow_run.state is None:
        return 0
    try:
        return int(flow_run.state.result())
    except Exception:
        return 0


@flow(name="ingest-eia-electricity-all", retries=2)
async def ingest_eia_electricity_all() -> dict[str, int]:
    """Run all EIA electricity ingests (retail-sales, electric-power-operational, source-disposition, state-summary).

    Each ingest is submitted as a separate deployment run so multiple workers
    can run them in parallel. Returns a summary of rows upserted per dataset.

    :returns: Dict mapping dataset name to rows upserted.
    """
    logger = get_run_logger()
    settings = Settings()
    if not settings.eia_api_key:
        raise ValueError("EIA_API_KEY is required for ingest_eia_electricity_all")
    if not settings.database_url:
        raise ValueError("DATABASE_URL is required for ingest_eia_electricity_all")

    # Submit all four as separate runs (no wait); work pool assigns each to a worker.
    logger.info("Submitting four ingest deployment runs to work pool...")
    runs = await asyncio.gather(
        run_deployment(DEPLOYMENT_NAMES[0], timeout=0, as_subflow=False),
        run_deployment(DEPLOYMENT_NAMES[1], timeout=0, as_subflow=False),
        run_deployment(DEPLOYMENT_NAMES[2], timeout=0, as_subflow=False),
        run_deployment(DEPLOYMENT_NAMES[3], timeout=0, as_subflow=False),
    )

    # Wait for all to complete (each may run on a different worker).
    logger.info("Waiting for all ingest runs to complete...")
    finished = await asyncio.gather(
        wait_for_flow_run(flow_run_id=runs[0].id),
        wait_for_flow_run(flow_run_id=runs[1].id),
        wait_for_flow_run(flow_run_id=runs[2].id),
        wait_for_flow_run(flow_run_id=runs[3].id),
    )

    summary = {
        "retail_sales": _result_from_flow_run(finished[0]),
        "electric_power_operational": _result_from_flow_run(finished[1]),
        "state_source_disposition": _result_from_flow_run(finished[2]),
        "state_summary": _result_from_flow_run(finished[3]),
    }
    logger.info("Ingest all complete: %s", summary)
    return summary
