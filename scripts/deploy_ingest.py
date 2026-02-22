#!/usr/bin/env -S uv run python
"""Register the EIA retail-sales ingest flow as a Prefect deployment with a monthly schedule.

Run once after the Prefect server and worker are up. Requires PREFECT_API_URL
(e.g. http://localhost:4200/api) and a process work pool named process-pool.

  uv run python scripts/deploy_ingest.py

Or from repo root with env set:

  PREFECT_API_URL=http://localhost:4200/api uv run python scripts/deploy_ingest.py
"""
import asyncio

from prefect.deployments.runner import RunnerDeployment

from energy_usa.flows.eia_retail_sales import ingest_eia_retail_sales


async def main() -> None:
    deployment = RunnerDeployment.from_flow(
        ingest_eia_retail_sales,
        name="ingest-eia-retail-sales",
        work_pool_name="process-pool",
        cron="0 0 1 * *",  # 1st of month at 00:00 UTC
        tags=["ingest", "eia"],
    )
    await deployment.apply()
    print(
        "Deployment applied. Ingest runs monthly (1st at 00:00 UTC). "
        "Trigger from Prefect UI or: prefect deployment run 'ingest-eia-retail-sales/ingest-eia-retail-sales'"
    )


if __name__ == "__main__":
    asyncio.run(main())
