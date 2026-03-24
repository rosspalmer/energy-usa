"""Database layer for ingest and future read endpoints.

This package provides a sync connection helper and upserts for EIA ingest tables.
No ORM; uses psycopg for direct SQL.
"""

from energy_usa.db.aeo import upsert_aeo
from energy_usa.db.biomass_capacity import upsert_biomass_capacity
from energy_usa.db.biomass_production import upsert_biomass_production
from energy_usa.db.coal_aggregate_production import upsert_coal_aggregate_production
from energy_usa.db.coal_consumption_quality import upsert_coal_consumption_quality
from energy_usa.db.coal_mine_production import upsert_coal_mine_production
from energy_usa.db.co2_emissions import upsert_co2_emissions
from energy_usa.db.crude_oil_imports import upsert_crude_oil_imports
from energy_usa.db.dataframe import query_to_dataframe
from energy_usa.db.electric_power_operational import upsert_electric_power_operational
from energy_usa.db.facility_fuel import upsert_facility_fuel
from energy_usa.db.ieo import upsert_ieo
from energy_usa.db.international import upsert_international
from energy_usa.db.natural_gas_consumption import upsert_natural_gas_consumption
from energy_usa.db.natural_gas_prices import upsert_natural_gas_prices
from energy_usa.db.natural_gas_production import upsert_natural_gas_production
from energy_usa.db.natural_gas_storage import upsert_natural_gas_storage
from energy_usa.db.nuclear_outages_facility import upsert_nuclear_outages_facility
from energy_usa.db.nuclear_outages_us import upsert_nuclear_outages_us
from energy_usa.db.operating_generator_capacity import upsert_operating_generator_capacity
from energy_usa.db.petroleum_prices import upsert_petroleum_prices
from energy_usa.db.petroleum_supply import upsert_petroleum_supply
from energy_usa.db.retail_sales import get_connection, upsert_retail_sales
from energy_usa.db.rto_daily_region_data import upsert_rto_daily_region_data
from energy_usa.db.rto_fuel_type_data import upsert_rto_fuel_type_data
from energy_usa.db.rto_interchange_data import upsert_rto_interchange_data
from energy_usa.db.rto_region_data import upsert_rto_region_data
from energy_usa.db.rto_region_sub_ba_data import upsert_rto_region_sub_ba_data
from energy_usa.db.seds import upsert_seds
from energy_usa.db.sep_capability import upsert_sep_capability
from energy_usa.db.sep_emissions import upsert_sep_emissions
from energy_usa.db.sep_net_metering import upsert_sep_net_metering
from energy_usa.db.state_source_disposition import upsert_state_source_disposition
from energy_usa.db.state_summary import upsert_state_summary
from energy_usa.db.steo import upsert_steo
from energy_usa.db.total_energy import upsert_total_energy

__all__ = [
    "get_connection",
    "query_to_dataframe",
    # Original four
    "upsert_retail_sales",
    "upsert_electric_power_operational",
    "upsert_state_source_disposition",
    "upsert_state_summary",
    # Electricity extras
    "upsert_rto_region_data",
    "upsert_rto_fuel_type_data",
    "upsert_rto_region_sub_ba_data",
    "upsert_rto_interchange_data",
    "upsert_rto_daily_region_data",
    "upsert_facility_fuel",
    "upsert_operating_generator_capacity",
    "upsert_sep_emissions",
    "upsert_sep_capability",
    "upsert_sep_net_metering",
    # Coal
    "upsert_coal_aggregate_production",
    "upsert_coal_consumption_quality",
    "upsert_coal_mine_production",
    # Crude oil
    "upsert_crude_oil_imports",
    # Nuclear
    "upsert_nuclear_outages_us",
    "upsert_nuclear_outages_facility",
    # Environment
    "upsert_co2_emissions",
    # Natural gas
    "upsert_natural_gas_prices",
    "upsert_natural_gas_consumption",
    "upsert_natural_gas_production",
    "upsert_natural_gas_storage",
    # Petroleum
    "upsert_petroleum_prices",
    "upsert_petroleum_supply",
    # Aggregate / cross-sector
    "upsert_total_energy",
    "upsert_seds",
    "upsert_steo",
    "upsert_international",
    # Biomass
    "upsert_biomass_capacity",
    "upsert_biomass_production",
    # Projections
    "upsert_aeo",
    "upsert_ieo",
]
