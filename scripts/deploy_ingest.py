#!/usr/bin/env -S uv run python
"""Register EIA ingest flows as Prefect deployments with explicit cadence.

Run once after the Prefect server and worker are up. Requires PREFECT_API_URL
(e.g. http://localhost:4200/api) and a process work pool named process-pool.

  uv run python scripts/deploy_ingest.py

Or from repo root with env set:

  PREFECT_API_URL=http://localhost:4200/api uv run python scripts/deploy_ingest.py
"""
import asyncio

from prefect.deployments.runner import EntrypointType, RunnerDeployment

from energy_usa.flows.backfill_eia import backfill_eia
from energy_usa.flows.eia_aeo import ingest_eia_aeo
from energy_usa.flows.eia_biomass_capacity import ingest_eia_biomass_capacity
from energy_usa.flows.eia_biomass_production import ingest_eia_biomass_production
from energy_usa.flows.eia_coal_aggregate_production import ingest_eia_coal_aggregate_production
from energy_usa.flows.eia_coal_consumption_quality import ingest_eia_coal_consumption_quality
from energy_usa.flows.eia_coal_mine_production import ingest_eia_coal_mine_production
from energy_usa.flows.eia_co2_emissions import ingest_eia_co2_emissions
from energy_usa.flows.eia_crude_oil_imports import ingest_eia_crude_oil_imports
from energy_usa.flows.eia_electric_power_operational import ingest_eia_electric_power_operational
from energy_usa.flows.eia_facility_fuel import ingest_eia_facility_fuel
from energy_usa.flows.eia_ieo import ingest_eia_ieo
from energy_usa.flows.eia_international import ingest_eia_international
from energy_usa.flows.eia_natural_gas_consumption import ingest_eia_natural_gas_consumption
from energy_usa.flows.eia_natural_gas_prices import ingest_eia_natural_gas_prices
from energy_usa.flows.eia_natural_gas_production import ingest_eia_natural_gas_production
from energy_usa.flows.eia_natural_gas_storage import ingest_eia_natural_gas_storage
from energy_usa.flows.eia_nuclear_outages_facility import ingest_eia_nuclear_outages_facility
from energy_usa.flows.eia_nuclear_outages_us import ingest_eia_nuclear_outages_us
from energy_usa.flows.eia_operating_generator_capacity import ingest_eia_operating_generator_capacity
from energy_usa.flows.eia_petroleum_prices import ingest_eia_petroleum_prices
from energy_usa.flows.eia_petroleum_supply import ingest_eia_petroleum_supply
from energy_usa.flows.eia_retail_sales import ingest_eia_retail_sales
from energy_usa.flows.eia_rto_daily_region_data import ingest_eia_rto_daily_region_data
from energy_usa.flows.eia_rto_fuel_type_data import ingest_eia_rto_fuel_type_data
from energy_usa.flows.eia_rto_interchange_data import ingest_eia_rto_interchange_data
from energy_usa.flows.eia_rto_region_data import ingest_eia_rto_region_data
from energy_usa.flows.eia_rto_region_sub_ba_data import ingest_eia_rto_region_sub_ba_data
from energy_usa.flows.eia_seds import ingest_eia_seds
from energy_usa.flows.eia_sep_capability import ingest_eia_sep_capability
from energy_usa.flows.eia_sep_emissions import ingest_eia_sep_emissions
from energy_usa.flows.eia_sep_net_metering import ingest_eia_sep_net_metering
from energy_usa.flows.eia_state_source_disposition import ingest_eia_state_source_disposition
from energy_usa.flows.eia_state_summary import ingest_eia_state_summary
from energy_usa.flows.eia_steo import ingest_eia_steo
from energy_usa.flows.eia_total_energy import ingest_eia_total_energy

# Cron schedules
MONTHLY_CRON = "0 0 1 * *"    # 1st of month at 00:00 UTC
QUARTERLY_CRON = "0 0 1 1,4,7,10 *"  # 1st of Jan/Apr/Jul/Oct
ANNUAL_CRON = "0 0 2 1 *"     # Jan 2 at 00:00 UTC (after year-end data lands)
DAILY_CRON = "0 6 * * *"      # 06:00 UTC daily

INGEST_DEPLOYMENTS = [
    # --- Original four (monthly electricity data) ---
    {"flow": ingest_eia_retail_sales, "name": "ingest-eia-retail-sales",
     "cron": MONTHLY_CRON, "run_cadence": "monthly", "source_frequency": "monthly"},
    {"flow": ingest_eia_electric_power_operational, "name": "ingest-eia-electric-power-operational",
     "cron": MONTHLY_CRON, "run_cadence": "monthly", "source_frequency": "monthly"},
    {"flow": ingest_eia_state_source_disposition, "name": "ingest-eia-state-source-disposition",
     "cron": MONTHLY_CRON, "run_cadence": "monthly", "source_frequency": "monthly"},
    {"flow": ingest_eia_state_summary, "name": "ingest-eia-state-summary",
     "cron": MONTHLY_CRON, "run_cadence": "monthly", "source_frequency": "annual"},

    # --- Electricity extras (RTO hourly/daily — run daily to catch recent hours) ---
    {"flow": ingest_eia_rto_region_data, "name": "ingest-eia-rto-region-data",
     "cron": DAILY_CRON, "run_cadence": "daily", "source_frequency": "hourly"},
    {"flow": ingest_eia_rto_fuel_type_data, "name": "ingest-eia-rto-fuel-type-data",
     "cron": DAILY_CRON, "run_cadence": "daily", "source_frequency": "hourly"},
    {"flow": ingest_eia_rto_region_sub_ba_data, "name": "ingest-eia-rto-region-sub-ba-data",
     "cron": DAILY_CRON, "run_cadence": "daily", "source_frequency": "hourly"},
    {"flow": ingest_eia_rto_interchange_data, "name": "ingest-eia-rto-interchange-data",
     "cron": DAILY_CRON, "run_cadence": "daily", "source_frequency": "hourly"},
    {"flow": ingest_eia_rto_daily_region_data, "name": "ingest-eia-rto-daily-region-data",
     "cron": DAILY_CRON, "run_cadence": "daily", "source_frequency": "daily"},

    # --- Electricity facility-level (annual) ---
    {"flow": ingest_eia_facility_fuel, "name": "ingest-eia-facility-fuel",
     "cron": ANNUAL_CRON, "run_cadence": "annual", "source_frequency": "annual"},
    {"flow": ingest_eia_operating_generator_capacity, "name": "ingest-eia-operating-generator-capacity",
     "cron": ANNUAL_CRON, "run_cadence": "annual", "source_frequency": "annual"},

    # --- SEP (State Energy Portal — annual) ---
    {"flow": ingest_eia_sep_emissions, "name": "ingest-eia-sep-emissions",
     "cron": ANNUAL_CRON, "run_cadence": "annual", "source_frequency": "annual"},
    {"flow": ingest_eia_sep_capability, "name": "ingest-eia-sep-capability",
     "cron": ANNUAL_CRON, "run_cadence": "annual", "source_frequency": "annual"},
    {"flow": ingest_eia_sep_net_metering, "name": "ingest-eia-sep-net-metering",
     "cron": ANNUAL_CRON, "run_cadence": "annual", "source_frequency": "annual"},

    # --- Coal (quarterly) ---
    {"flow": ingest_eia_coal_aggregate_production, "name": "ingest-eia-coal-aggregate-production",
     "cron": QUARTERLY_CRON, "run_cadence": "quarterly", "source_frequency": "quarterly"},
    {"flow": ingest_eia_coal_consumption_quality, "name": "ingest-eia-coal-consumption-quality",
     "cron": QUARTERLY_CRON, "run_cadence": "quarterly", "source_frequency": "quarterly"},
    {"flow": ingest_eia_coal_mine_production, "name": "ingest-eia-coal-mine-production",
     "cron": QUARTERLY_CRON, "run_cadence": "quarterly", "source_frequency": "quarterly"},

    # --- Crude oil imports (monthly) ---
    {"flow": ingest_eia_crude_oil_imports, "name": "ingest-eia-crude-oil-imports",
     "cron": MONTHLY_CRON, "run_cadence": "monthly", "source_frequency": "monthly"},

    # --- Nuclear outages (daily) ---
    {"flow": ingest_eia_nuclear_outages_us, "name": "ingest-eia-nuclear-outages-us",
     "cron": DAILY_CRON, "run_cadence": "daily", "source_frequency": "daily"},
    {"flow": ingest_eia_nuclear_outages_facility, "name": "ingest-eia-nuclear-outages-facility",
     "cron": DAILY_CRON, "run_cadence": "daily", "source_frequency": "daily"},

    # --- CO2 emissions (annual) ---
    {"flow": ingest_eia_co2_emissions, "name": "ingest-eia-co2-emissions",
     "cron": ANNUAL_CRON, "run_cadence": "annual", "source_frequency": "annual"},

    # --- Natural gas (monthly) ---
    {"flow": ingest_eia_natural_gas_prices, "name": "ingest-eia-natural-gas-prices",
     "cron": MONTHLY_CRON, "run_cadence": "monthly", "source_frequency": "monthly"},
    {"flow": ingest_eia_natural_gas_consumption, "name": "ingest-eia-natural-gas-consumption",
     "cron": MONTHLY_CRON, "run_cadence": "monthly", "source_frequency": "monthly"},
    {"flow": ingest_eia_natural_gas_production, "name": "ingest-eia-natural-gas-production",
     "cron": MONTHLY_CRON, "run_cadence": "monthly", "source_frequency": "monthly"},
    {"flow": ingest_eia_natural_gas_storage, "name": "ingest-eia-natural-gas-storage",
     "cron": MONTHLY_CRON, "run_cadence": "monthly", "source_frequency": "weekly"},

    # --- Petroleum (monthly) ---
    {"flow": ingest_eia_petroleum_prices, "name": "ingest-eia-petroleum-prices",
     "cron": MONTHLY_CRON, "run_cadence": "monthly", "source_frequency": "monthly"},
    {"flow": ingest_eia_petroleum_supply, "name": "ingest-eia-petroleum-supply",
     "cron": MONTHLY_CRON, "run_cadence": "monthly", "source_frequency": "monthly"},

    # --- Aggregate / cross-sector ---
    {"flow": ingest_eia_total_energy, "name": "ingest-eia-total-energy",
     "cron": MONTHLY_CRON, "run_cadence": "monthly", "source_frequency": "monthly"},
    {"flow": ingest_eia_seds, "name": "ingest-eia-seds",
     "cron": ANNUAL_CRON, "run_cadence": "annual", "source_frequency": "annual"},
    {"flow": ingest_eia_steo, "name": "ingest-eia-steo",
     "cron": MONTHLY_CRON, "run_cadence": "monthly", "source_frequency": "monthly"},
    {"flow": ingest_eia_international, "name": "ingest-eia-international",
     "cron": ANNUAL_CRON, "run_cadence": "annual", "source_frequency": "annual"},

    # --- Biomass (annual) ---
    {"flow": ingest_eia_biomass_capacity, "name": "ingest-eia-biomass-capacity",
     "cron": ANNUAL_CRON, "run_cadence": "annual", "source_frequency": "annual"},
    {"flow": ingest_eia_biomass_production, "name": "ingest-eia-biomass-production",
     "cron": ANNUAL_CRON, "run_cadence": "annual", "source_frequency": "annual"},

    # --- Projections (annual — latest vintage) ---
    {"flow": ingest_eia_aeo, "name": "ingest-eia-aeo",
     "cron": ANNUAL_CRON, "run_cadence": "annual", "source_frequency": "annual"},
    {"flow": ingest_eia_ieo, "name": "ingest-eia-ieo",
     "cron": ANNUAL_CRON, "run_cadence": "annual", "source_frequency": "annual"},
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
        f"Deployments applied: {len(deployments)} total "
        f"({len(INGEST_DEPLOYMENTS)} ingest + 1 backfill). "
        "Trigger from Prefect UI or: prefect deployment run '<flow-name>/<deployment-name>'. "
        "For backfill: prefect deployment run 'backfill-eia/backfill-eia' "
        "--param dataset=<name> --param date_start=YYYY-MM --param date_end=YYYY-MM"
    )


if __name__ == "__main__":
    asyncio.run(main())
