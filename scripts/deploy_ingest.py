#!/usr/bin/env -S uv run python
"""Register EIA electricity ingest flows as Prefect deployments with monthly schedules.

Run once after the Prefect server and worker are up. Requires PREFECT_API_URL
(e.g. http://localhost:4200/api) and a process work pool named process-pool.

  uv run python scripts/deploy_ingest.py

Or from repo root with env set:

  PREFECT_API_URL=http://localhost:4200/api uv run python scripts/deploy_ingest.py
"""
import asyncio

from prefect.deployments.runner import EntrypointType, RunnerDeployment

from energy_usa.flows.eia_electric_power_operational import ingest_eia_electric_power_operational
from energy_usa.flows.eia_electricity_all import ingest_eia_electricity_all
from energy_usa.flows.eia_retail_sales import ingest_eia_retail_sales
from energy_usa.flows.eia_state_source_disposition import ingest_eia_state_source_disposition
from energy_usa.flows.eia_state_summary import ingest_eia_state_summary

MONTHLY_CRON = "0 0 1 * *"  # 1st of month at 00:00 UTC


async def main() -> None:
    # Use MODULE_PATH so the worker loads the flow by importing the installed package
    # instead of a file path (which fails when Prefect uses a temp dir without our code).
    deployments = [
        RunnerDeployment.from_flow(
            ingest_eia_retail_sales,
            name="ingest-eia-retail-sales",
            work_pool_name="process-pool",
            cron=MONTHLY_CRON,
            tags=["ingest", "eia"],
            entrypoint_type=EntrypointType.MODULE_PATH,
        ),
        RunnerDeployment.from_flow(
            ingest_eia_electric_power_operational,
            name="ingest-eia-electric-power-operational",
            work_pool_name="process-pool",
            cron=MONTHLY_CRON,
            tags=["ingest", "eia"],
            entrypoint_type=EntrypointType.MODULE_PATH,
        ),
        RunnerDeployment.from_flow(
            ingest_eia_state_source_disposition,
            name="ingest-eia-state-source-disposition",
            work_pool_name="process-pool",
            cron=MONTHLY_CRON,
            tags=["ingest", "eia"],
            entrypoint_type=EntrypointType.MODULE_PATH,
        ),
        RunnerDeployment.from_flow(
            ingest_eia_state_summary,
            name="ingest-eia-state-summary",
            work_pool_name="process-pool",
            cron=MONTHLY_CRON,
            tags=["ingest", "eia"],
            entrypoint_type=EntrypointType.MODULE_PATH,
        ),
        RunnerDeployment.from_flow(
            ingest_eia_electricity_all,
            name="ingest-eia-electricity-all",
            work_pool_name="process-pool",
            cron=MONTHLY_CRON,
            tags=["ingest", "eia"],
            entrypoint_type=EntrypointType.MODULE_PATH,
        ),
    ]
    for deployment in deployments:
        await deployment.apply()
    print(
        "Deployments applied. All run monthly (1st at 00:00 UTC). "
        "Trigger from Prefect UI or: prefect deployment run 'ingest-eia-electricity-all/ingest-eia-electricity-all'"
    )


if __name__ == "__main__":
    asyncio.run(main())
