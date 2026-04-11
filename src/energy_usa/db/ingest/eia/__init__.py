"""EIA ingest database modules — one upsert function per dataset."""

from energy_usa.db.ingest.eia.aeo import upsert_aeo
from energy_usa.db.ingest.eia.biomass_capacity import upsert_biomass_capacity
from energy_usa.db.ingest.eia.biomass_production import upsert_biomass_production
from energy_usa.db.ingest.eia.coal_aggregate_production import upsert_coal_aggregate_production
from energy_usa.db.ingest.eia.coal_consumption_quality import upsert_coal_consumption_quality
from energy_usa.db.ingest.eia.coal_mine_production import upsert_coal_mine_production
from energy_usa.db.ingest.eia.co2_emissions import upsert_co2_emissions
from energy_usa.db.ingest.eia.crude_oil_imports import upsert_crude_oil_imports
from energy_usa.db.ingest.eia.electric_power_operational import upsert_electric_power_operational
from energy_usa.db.ingest.eia.facility_fuel import upsert_facility_fuel
from energy_usa.db.ingest.eia.ieo import upsert_ieo
from energy_usa.db.ingest.eia.international import upsert_international
from energy_usa.db.ingest.eia.natural_gas_consumption import upsert_natural_gas_consumption
from energy_usa.db.ingest.eia.natural_gas_prices import upsert_natural_gas_prices
from energy_usa.db.ingest.eia.natural_gas_production import upsert_natural_gas_production
from energy_usa.db.ingest.eia.natural_gas_storage import upsert_natural_gas_storage
from energy_usa.db.ingest.eia.nuclear_outages_facility import upsert_nuclear_outages_facility
from energy_usa.db.ingest.eia.nuclear_outages_us import upsert_nuclear_outages_us
from energy_usa.db.ingest.eia.operating_generator_capacity import upsert_operating_generator_capacity
from energy_usa.db.ingest.eia.petroleum_prices import upsert_petroleum_prices
from energy_usa.db.ingest.eia.petroleum_supply import upsert_petroleum_supply
from energy_usa.db.ingest.eia.retail_sales import upsert_retail_sales
from energy_usa.db.ingest.eia.rto_daily_region_data import upsert_rto_daily_region_data
from energy_usa.db.ingest.eia.rto_fuel_type_data import upsert_rto_fuel_type_data
from energy_usa.db.ingest.eia.rto_interchange_data import upsert_rto_interchange_data
from energy_usa.db.ingest.eia.rto_region_data import upsert_rto_region_data
from energy_usa.db.ingest.eia.rto_region_sub_ba_data import upsert_rto_region_sub_ba_data
from energy_usa.db.ingest.eia.seds import upsert_seds
from energy_usa.db.ingest.eia.sep_capability import upsert_sep_capability
from energy_usa.db.ingest.eia.sep_emissions import upsert_sep_emissions
from energy_usa.db.ingest.eia.sep_net_metering import upsert_sep_net_metering
from energy_usa.db.ingest.eia.state_source_disposition import upsert_state_source_disposition
from energy_usa.db.ingest.eia.state_summary import upsert_state_summary
from energy_usa.db.ingest.eia.steo import upsert_steo
from energy_usa.db.ingest.eia.total_energy import upsert_total_energy

__all__ = [
    "upsert_aeo",
    "upsert_biomass_capacity",
    "upsert_biomass_production",
    "upsert_coal_aggregate_production",
    "upsert_coal_consumption_quality",
    "upsert_coal_mine_production",
    "upsert_co2_emissions",
    "upsert_crude_oil_imports",
    "upsert_electric_power_operational",
    "upsert_facility_fuel",
    "upsert_ieo",
    "upsert_international",
    "upsert_natural_gas_consumption",
    "upsert_natural_gas_prices",
    "upsert_natural_gas_production",
    "upsert_natural_gas_storage",
    "upsert_nuclear_outages_facility",
    "upsert_nuclear_outages_us",
    "upsert_operating_generator_capacity",
    "upsert_petroleum_prices",
    "upsert_petroleum_supply",
    "upsert_retail_sales",
    "upsert_rto_daily_region_data",
    "upsert_rto_fuel_type_data",
    "upsert_rto_interchange_data",
    "upsert_rto_region_data",
    "upsert_rto_region_sub_ba_data",
    "upsert_seds",
    "upsert_sep_capability",
    "upsert_sep_emissions",
    "upsert_sep_net_metering",
    "upsert_state_source_disposition",
    "upsert_state_summary",
    "upsert_steo",
    "upsert_total_energy",
]
