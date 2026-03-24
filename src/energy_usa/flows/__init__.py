"""Prefect flows for scheduled ingest jobs."""

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

__all__ = [
    "backfill_eia",
    # Original four
    "ingest_eia_retail_sales",
    "ingest_eia_electric_power_operational",
    "ingest_eia_state_source_disposition",
    "ingest_eia_state_summary",
    # Electricity extras
    "ingest_eia_rto_region_data",
    "ingest_eia_rto_fuel_type_data",
    "ingest_eia_rto_region_sub_ba_data",
    "ingest_eia_rto_interchange_data",
    "ingest_eia_rto_daily_region_data",
    "ingest_eia_facility_fuel",
    "ingest_eia_operating_generator_capacity",
    "ingest_eia_sep_emissions",
    "ingest_eia_sep_capability",
    "ingest_eia_sep_net_metering",
    # Coal
    "ingest_eia_coal_aggregate_production",
    "ingest_eia_coal_consumption_quality",
    "ingest_eia_coal_mine_production",
    # Crude oil
    "ingest_eia_crude_oil_imports",
    # Nuclear
    "ingest_eia_nuclear_outages_us",
    "ingest_eia_nuclear_outages_facility",
    # Environment
    "ingest_eia_co2_emissions",
    # Natural gas
    "ingest_eia_natural_gas_prices",
    "ingest_eia_natural_gas_consumption",
    "ingest_eia_natural_gas_production",
    "ingest_eia_natural_gas_storage",
    # Petroleum
    "ingest_eia_petroleum_prices",
    "ingest_eia_petroleum_supply",
    # Aggregate / cross-sector
    "ingest_eia_total_energy",
    "ingest_eia_seds",
    "ingest_eia_steo",
    "ingest_eia_international",
    # Biomass
    "ingest_eia_biomass_capacity",
    "ingest_eia_biomass_production",
    # Projections
    "ingest_eia_aeo",
    "ingest_eia_ieo",
]
