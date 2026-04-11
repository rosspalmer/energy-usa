#!/usr/bin/env -S uv run python
"""Register EIA ingest flows as Prefect deployments.

Discovers flows dynamically from the flows.ingest.eia package.
Run once after the Prefect server and worker are up.
"""
import asyncio

from prefect.deployments.runner import EntrypointType, RunnerDeployment

from energy_usa.flows.ingest.backfill import backfill_eia, get_flow_registry

# Cron schedules
MONTHLY_CRON = "0 0 1 * *"
QUARTERLY_CRON = "0 0 1 1,4,7,10 *"
ANNUAL_CRON = "0 0 2 1 *"
DAILY_CRON = "0 6 * * *"

# Map dataset names to their run schedule. Datasets not listed here default to MONTHLY_CRON.
SCHEDULE_OVERRIDES: dict[str, str] = {
    "rto_region_data": DAILY_CRON,
    "rto_fuel_type_data": DAILY_CRON,
    "rto_region_sub_ba_data": DAILY_CRON,
    "rto_interchange_data": DAILY_CRON,
    "rto_daily_region_data": DAILY_CRON,
    "nuclear_outages_us": DAILY_CRON,
    "nuclear_outages_facility": DAILY_CRON,
    "facility_fuel": ANNUAL_CRON,
    "operating_generator_capacity": ANNUAL_CRON,
    "sep_emissions": ANNUAL_CRON,
    "sep_capability": ANNUAL_CRON,
    "sep_net_metering": ANNUAL_CRON,
    "coal_aggregate_production": QUARTERLY_CRON,
    "coal_consumption_quality": QUARTERLY_CRON,
    "coal_mine_production": QUARTERLY_CRON,
    "co2_emissions": ANNUAL_CRON,
    "seds": ANNUAL_CRON,
    "international": ANNUAL_CRON,
    "biomass_capacity": ANNUAL_CRON,
    "biomass_production": ANNUAL_CRON,
    "aeo": ANNUAL_CRON,
    "ieo": ANNUAL_CRON,
}


async def main() -> None:
    registry = get_flow_registry("eia")
    deployments = []

    for dataset_name, flow_fn in sorted(registry.items()):
        cron = SCHEDULE_OVERRIDES.get(dataset_name, MONTHLY_CRON)
        name = f"ingest-eia-{dataset_name.replace('_', '-')}"
        deployments.append(
            RunnerDeployment.from_flow(
                flow_fn,
                name=name,
                work_pool_name="process-pool",
                cron=cron,
                tags=["ingest", "eia"],
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
        f"Deployments applied: {len(deployments)} total "
        f"({len(deployments) - 1} ingest + 1 backfill)."
    )


if __name__ == "__main__":
    asyncio.run(main())
