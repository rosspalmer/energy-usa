"""Prefect flow to backfill EIA datasets in configurable month chunks.

The parent flow splits a date range (YYYY-MM to YYYY-MM) into chunks of N
months and submits one child ingest flow run per chunk. If date bounds are
omitted, it defaults to the same range behavior as ingest flows.
"""

import asyncio
from typing import Any, Awaitable, Callable, Literal

from prefect import flow
from prefect.logging import get_run_logger

from energy_usa.flows.date_range import monthly_chunks, resolve_date_range
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

DatasetName = Literal[
    # Original four
    "retail_sales",
    "electric_power_operational",
    "state_source_disposition",
    "state_summary",
    # Electricity extras
    "rto_region_data",
    "rto_fuel_type_data",
    "rto_region_sub_ba_data",
    "rto_interchange_data",
    "rto_daily_region_data",
    "facility_fuel",
    "operating_generator_capacity",
    "sep_emissions",
    "sep_capability",
    "sep_net_metering",
    # Coal
    "coal_aggregate_production",
    "coal_consumption_quality",
    "coal_mine_production",
    # Crude oil
    "crude_oil_imports",
    # Nuclear
    "nuclear_outages_us",
    "nuclear_outages_facility",
    # Environment
    "co2_emissions",
    # Natural gas
    "natural_gas_prices",
    "natural_gas_consumption",
    "natural_gas_production",
    "natural_gas_storage",
    # Petroleum
    "petroleum_prices",
    "petroleum_supply",
    # Aggregate / cross-sector
    "total_energy",
    "seds",
    "steo",
    "international",
    # Biomass
    "biomass_capacity",
    "biomass_production",
    # Projections
    "aeo",
    "ieo",
    "all",
]

IngestFlow = Callable[..., Awaitable[int]]

# All datasets in order for "all" runs.
_FLOW_REGISTRY: list[tuple[str, IngestFlow]] = [
    ("retail_sales", ingest_eia_retail_sales),
    ("electric_power_operational", ingest_eia_electric_power_operational),
    ("state_source_disposition", ingest_eia_state_source_disposition),
    ("state_summary", ingest_eia_state_summary),
    ("rto_region_data", ingest_eia_rto_region_data),
    ("rto_fuel_type_data", ingest_eia_rto_fuel_type_data),
    ("rto_region_sub_ba_data", ingest_eia_rto_region_sub_ba_data),
    ("rto_interchange_data", ingest_eia_rto_interchange_data),
    ("rto_daily_region_data", ingest_eia_rto_daily_region_data),
    ("facility_fuel", ingest_eia_facility_fuel),
    ("operating_generator_capacity", ingest_eia_operating_generator_capacity),
    ("sep_emissions", ingest_eia_sep_emissions),
    ("sep_capability", ingest_eia_sep_capability),
    ("sep_net_metering", ingest_eia_sep_net_metering),
    ("coal_aggregate_production", ingest_eia_coal_aggregate_production),
    ("coal_consumption_quality", ingest_eia_coal_consumption_quality),
    ("coal_mine_production", ingest_eia_coal_mine_production),
    ("crude_oil_imports", ingest_eia_crude_oil_imports),
    ("nuclear_outages_us", ingest_eia_nuclear_outages_us),
    ("nuclear_outages_facility", ingest_eia_nuclear_outages_facility),
    ("co2_emissions", ingest_eia_co2_emissions),
    ("natural_gas_prices", ingest_eia_natural_gas_prices),
    ("natural_gas_consumption", ingest_eia_natural_gas_consumption),
    ("natural_gas_production", ingest_eia_natural_gas_production),
    ("natural_gas_storage", ingest_eia_natural_gas_storage),
    ("petroleum_prices", ingest_eia_petroleum_prices),
    ("petroleum_supply", ingest_eia_petroleum_supply),
    ("total_energy", ingest_eia_total_energy),
    ("seds", ingest_eia_seds),
    ("steo", ingest_eia_steo),
    ("international", ingest_eia_international),
    ("biomass_capacity", ingest_eia_biomass_capacity),
    ("biomass_production", ingest_eia_biomass_production),
    ("aeo", ingest_eia_aeo),
    ("ieo", ingest_eia_ieo),
]

_FLOW_MAP: dict[str, tuple[str, IngestFlow]] = {name: (name, fn) for name, fn in _FLOW_REGISTRY}


def _get_ingest_flows(dataset: DatasetName) -> list[tuple[str, IngestFlow]]:
    """Resolve dataset selector to one or more ingest flow callables."""
    if dataset == "all":
        return list(_FLOW_REGISTRY)
    if dataset not in _FLOW_MAP:
        valid = ", ".join([*_FLOW_MAP.keys(), "all"])
        raise ValueError(f"Invalid dataset '{dataset}'. Expected one of: {valid}")
    return [_FLOW_MAP[dataset]]


@flow(name="backfill-eia", retries=1)
async def backfill_eia(
    date_start: str | None = None,
    date_end: str | None = None,
    chunk_months: int = 1,
    dataset: DatasetName = "retail_sales",
) -> dict[str, Any]:
    """Submit EIA backfill ingest runs in contiguous month chunks.

    :param date_start: Optional start period (YYYY-MM). Defaults to last calendar month.
    :param date_end: Optional end period (YYYY-MM). Defaults to current month.
    :param chunk_months: Number of months per child run; must be >= 1.
    :param dataset: Dataset selector or "all".
    :returns: Summary dict with chunk count and child flow results.
    """
    logger = get_run_logger()
    start, end = resolve_date_range(date_start, date_end)
    chunks = list(monthly_chunks(start, end, chunk_months=chunk_months))
    selected_flows = _get_ingest_flows(dataset)
    logger.info(
        "Backfill start: start=%s end=%s chunk_months=%s chunks=%s datasets=%s",
        start,
        end,
        chunk_months,
        len(chunks),
        [name for name, _flow in selected_flows],
    )

    submitted: list[tuple[str, str, str, asyncio.Task[int]]] = []
    for chunk_start, chunk_end in chunks:
        for dataset_name, ingest_flow in selected_flows:
            logger.info(
                "Starting child ingest flow: dataset=%s start=%s end=%s",
                dataset_name,
                chunk_start,
                chunk_end,
            )
            child_task = asyncio.create_task(
                ingest_flow(
                    date_start=chunk_start,
                    date_end=chunk_end,
                )
            )
            submitted.append((dataset_name, chunk_start, chunk_end, child_task))

    runs: list[dict[str, Any]] = []
    for dataset_name, chunk_start, chunk_end, child_task in submitted:
        rows_upserted = await child_task
        runs.append(
            {
                "dataset": dataset_name,
                "date_start": chunk_start,
                "date_end": chunk_end,
                "rows_upserted": rows_upserted,
            }
        )

    logger.info("Backfill complete: child_runs=%s", len(runs))
    return {"chunks": len(chunks), "total_runs": len(runs), "runs": runs}
