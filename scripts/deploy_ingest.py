#!/usr/bin/env -S uv run python
"""Register EIA electricity ingest flows as Prefect deployments with explicit cadence.

Run once after the Prefect server and worker are up. Requires PREFECT_API_URL
(e.g. http://localhost:4200/api) and a process work pool named process-pool.

  uv run python scripts/deploy_ingest.py

Or from repo root with env set:

  PREFECT_API_URL=http://localhost:4200/api uv run python scripts/deploy_ingest.py
"""
import asyncio

from prefect.deployments.runner import EntrypointType, RunnerDeployment

from energy_usa.flows.backfill_eia import backfill_eia
from energy_usa.flows.eia_electric_power_operational import ingest_eia_electric_power_operational
from energy_usa.flows.eia_retail_sales import ingest_eia_retail_sales
from energy_usa.flows.eia_state_source_disposition import ingest_eia_state_source_disposition
from energy_usa.flows.eia_state_summary import ingest_eia_state_summary

# Cadence: run_cadence = schedule frequency; source_frequency = EIA data grain (monthly vs annual).
RUN_CADENCE_MONTHLY_CRON = "0 0 1 * *"  # 1st of month at 00:00 UTC

INGEST_DEPLOYMENTS = [
    {
        "flow": ingest_eia_retail_sales,
        "name": "ingest-eia-retail-sales",
        "cron": RUN_CADENCE_MONTHLY_CRON,
        "run_cadence": "monthly",
        "source_frequency": "monthly",
    },
    {
        "flow": ingest_eia_electric_power_operational,
        "name": "ingest-eia-electric-power-operational",
        "cron": RUN_CADENCE_MONTHLY_CRON,
        "run_cadence": "monthly",
        "source_frequency": "monthly",
    },
    {
        "flow": ingest_eia_state_source_disposition,
        "name": "ingest-eia-state-source-disposition",
        "cron": RUN_CADENCE_MONTHLY_CRON,
        "run_cadence": "monthly",
        "source_frequency": "monthly",
    },
    {
        "flow": ingest_eia_state_summary,
        "name": "ingest-eia-state-summary",
        "cron": RUN_CADENCE_MONTHLY_CRON,
        "run_cadence": "monthly",
        "source_frequency": "annual",
    },
]


async def main() -> None:
    # Use MODULE_PATH so the worker loads the flow by importing the installed package
    # instead of a file path (which fails when Prefect uses a temp dir without our code).
    deployments = []
    for cfg in INGEST_DEPLOYMENTS:
        deployments.append(
            RunnerDeployment.from_flow(
                cfg["flow"],
                name=cfg["name"],
                work_pool_name="process-pool",
                cron=cfg["cron"],
                tags=[
                    "ingest",
                    "eia",
                    f"run_cadence:{cfg['run_cadence']}",
                    f"source_frequency:{cfg['source_frequency']}",
                ],
                entrypoint_type=EntrypointType.MODULE_PATH,
            )
        )
    deployments.append(
        RunnerDeployment.from_flow(
            backfill_eia,
            name="backfill-eia",
            work_pool_name="process-pool",
            parameters={
                "date_start": None,
                "date_end": None,
                "chunk_months": 1,
                "dataset": "retail_sales",
            },
            tags=["backfill", "eia"],
            entrypoint_type=EntrypointType.MODULE_PATH,
        ),
    )
    for deployment in deployments:
        await deployment.apply()
    print(
        "Deployments applied. Four ingest deployments run monthly (1st at 00:00 UTC), "
        "and one backfill deployment runs on demand. "
        "Trigger from Prefect UI or run individually, e.g. prefect deployment run 'ingest-eia-retail-sales/ingest-eia-retail-sales'. "
        "For backfill, run 'backfill-eia/backfill-eia' with optional date parameters: "
        "--param date_start=YYYY-MM --param date_end=YYYY-MM --param chunk_months=N --param dataset=retail_sales|electric_power_operational|state_source_disposition|state_summary|all"
    )


if __name__ == "__main__":
    asyncio.run(main())
