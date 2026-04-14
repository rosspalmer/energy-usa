# EIA — U.S. Energy Information Administration

## Source
- **Type**: rest-json
- **Base URL**: https://api.eia.gov/v2
- **Auth**: API key via query param `api_key`, env var `EIA_API_KEY`
- **Pagination**: offset-based, `offset` + `length` params, response `total` field
- **Rate limit**: 4 concurrent requests, 500ms page delay

## Datasets

### aeo
- **API path**: aeo/2023/data
- **API method**: route
- **Frequency**: annual
- **Unique key**: (period, aeo_year, scenario, series_id)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | aeo_year | aeo_year | TEXT | yes | |
  | scenario | scenario; scenarioId; caseid | TEXT | yes | ref |
  | series_id | seriesId; series_id; series; msn | TEXT | yes | NA |
  | series_description | seriesDescription; series-description; series_description | TEXT | no | |
  | value | value | NUMERIC | no | |
  | unit | unit; units | TEXT | no | |
- **History**: 2015-01

### biomass_capacity
- **API path**: densified-biomass/capacity-by-region/data
- **API method**: route
- **Frequency**: annual
- **Unique key**: (period, region_id)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | region_id | regionId; region_id; region | TEXT | yes | NA |
  | region_name | regionName; region_name | TEXT | no | |
  | capacity | capacity | NUMERIC | no | |
  | unit | unit; units | TEXT | no | thousand short tons per year |
- **History**: 2012-01

### biomass_production
- **API path**: densified-biomass/production-by-region/data
- **API method**: route
- **Frequency**: annual
- **Unique key**: (period, region_id)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | region_id | regionId; region_id; region | TEXT | yes | NA |
  | region_name | regionName; region_name | TEXT | no | |
  | production | production | NUMERIC | no | |
  | unit | unit; units | TEXT | no | thousand short tons |
- **History**: 2012-01

### co2_emissions
- **API path**: co2-emissions/co2-emissions-aggregates/data
- **API method**: route
- **Frequency**: annual
- **Extra API params**: frequency=annual
- **Unique key**: (period, state_id, sector_id, fuel_id)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | state_id | stateId; state_id; stateid | TEXT | yes | US |
  | state_description | stateDescription; state_description | TEXT | no | |
  | sector_id | sectorId; sector_id; sectorid | TEXT | yes | ALL |
  | sector_description | sectorDescription; sector_description | TEXT | no | |
  | fuel_id | fuelId; fuel_id; fuelid | TEXT | yes | ALL |
  | fuel_description | fuelDescription; fuel_description | TEXT | no | |
  | value | value | NUMERIC | no | |
  | value_units | value-units; valueUnits | TEXT | no | million metric tons CO2 |
- **History**: 1970-01

### coal_aggregate_production
- **API path**: coal/aggregate-production/data
- **API method**: route
- **Frequency**: quarterly
- **Unique key**: (period, location, coal_rank_id)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | TEXT | yes | |
  | location | location; locationId; stateId | TEXT | yes | US |
  | coal_rank_id | coalRankId; coal_rank_id; coalrank | TEXT | yes | ALL |
  | coal_rank_description | coalRankDescription; coal_rank_description | TEXT | no | |
  | production | production | NUMERIC | no | |
  | production_units | production-units; productionUnits | TEXT | no | thousand short tons |
- **History**: 2000-01

### coal_consumption_quality
- **API path**: coal/consumption-and-quality/data
- **API method**: route
- **Frequency**: quarterly
- **Unique key**: (period, location, sector_id, coal_rank_id)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | TEXT | yes | |
  | location | location; stateId | TEXT | yes | US |
  | sector_id | sectorId; sector_id; sector | TEXT | yes | ALL |
  | coal_rank_id | coalRankId; coal_rank_id | TEXT | yes | ALL |
  | coal_rank_description | coalRankDescription; coal_rank_description | TEXT | no | |
  | consumption | consumption | NUMERIC | no | |
  | consumption_units | consumption-units | TEXT | no | thousand short tons |
  | average_heat_content | heat-content; average-heat-content; averageHeatContent | NUMERIC | no | |
  | average_sulfur_content | sulfur-content; average-sulfur-content; averageSulfurContent | NUMERIC | no | |
  | average_ash_content | ash-content; average-ash-content; averageAshContent | NUMERIC | no | |
- **History**: 2000-01

### coal_mine_production
- **API path**: coal/mine-production/data
- **API method**: route
- **Frequency**: quarterly
- **Unique key**: (period, mine_state, mine_type, coal_rank_id)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | TEXT | yes | |
  | mine_state | mineState; mine_state; stateId | TEXT | yes | US |
  | mine_type | mineType; mine_type; mineTypeId | TEXT | yes | ALL |
  | coal_rank_id | coalRankId; coal_rank_id | TEXT | yes | ALL |
  | coal_rank_description | coalRankDescription; coal_rank_description | TEXT | no | |
  | production | production | NUMERIC | no | |
  | production_units | production-units | TEXT | no | thousand short tons |
- **History**: 2000-01

### crude_oil_imports
- **API path**: crude-oil-imports/data
- **API method**: route
- **Frequency**: monthly
- **Unique key**: (period, origin_id, destination_id, grade_id, refiner_type)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | origin_id | originId; origin_id; originCode | TEXT | yes | UNK |
  | origin_name | originName; origin_name | TEXT | no | |
  | destination_id | destinationId; destination_id; destinationCode | TEXT | yes | UNK |
  | destination_name | destinationName; destination_name | TEXT | no | |
  | grade_id | gradeId; grade_id; gradeCode | TEXT | yes | UNK |
  | grade_name | gradeName; grade_name | TEXT | no | |
  | refiner_type | refinerType; refiner_type; refinerTypeId | TEXT | yes | UNK |
  | quantity | quantity | NUMERIC | no | |
  | quantity_units | quantity-units | TEXT | no | thousand barrels |
- **History**: 2001-01

### electric_power_operational
- **API path**: /electricity/electric-power-operational-data/data
- **API method**: electricity
- **Frequency**: monthly
- **Unique key**: (period, stateid, sectorid, fueltypeid)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | stateid | stateid; stateId; state; location | TEXT | yes | |
  | sectorid | sectorid; sectorId | TEXT | yes | |
  | fueltypeid | fueltypeid; fueltypeId; typeid; typeId | TEXT | yes | |
  | generation | generation; net-generation | NUMERIC | no | |
- **Filters**: Skip rows where stateid = 'ALL'
- **History**: 2001-01

### facility_fuel
- **API path**: /electricity/facility-fuel/data
- **API method**: electricity
- **Frequency**: annual
- **Extra API params**: frequency=annual
- **Unique key**: (period, plantid, fuel_type)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | plantid | plantid | TEXT | yes | |
  | plant_name | plantName; plant_name | TEXT | no | |
  | state | state; stateid | TEXT | no | |
  | state_description | stateDescription; state_description | TEXT | no | |
  | fuel_type | fuel2002; fuel_type; fuelTypeId | TEXT | yes | |
  | fuel_type_description | fuelTypeDescription; fuel_type_description | TEXT | no | |
  | prime_mover | primeMover; prime_mover | TEXT | no | |
  | generation | generation | NUMERIC | no | |
  | consumption_ej | consumption_ej | NUMERIC | no | |
  | consumption_mmbtus | total-consumption-btu; consumption-mmbtus; consumption_mmbtus | NUMERIC | no | |
- **History**: 2001-01

### ieo
- **API path**: ieo/2023/data
- **API method**: route
- **Frequency**: annual
- **Unique key**: (period, ieo_year, region_id, series_id)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | ieo_year | ieo_year | TEXT | yes | |
  | region_id | regionId; region_id; region | TEXT | yes | WORLD |
  | region_name | regionName; region_name | TEXT | no | |
  | series_id | seriesId; series_id; series | TEXT | yes | NA |
  | series_description | seriesDescription; series-description; series_description | TEXT | no | |
  | value | value | NUMERIC | no | |
  | unit | unit; units | TEXT | no | |
- **History**: 2015-01

### international
- **API path**: international/data
- **API method**: route
- **Frequency**: annual
- **Extra API params**: frequency=annual
- **Unique key**: (period, activity_id, product_id, country_region_id, unit)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | activity_id | activityId; activity_id; activity | TEXT | yes | NA |
  | activity_name | activityName; activity_name | TEXT | no | |
  | product_id | productId; product_id; product | TEXT | yes | NA |
  | product_name | productName; product_name | TEXT | no | |
  | country_region_id | countryRegionId; country_region_id; countryId | TEXT | yes | WORL |
  | country_region_name | countryRegionName; country_region_name; countryName | TEXT | no | |
  | unit | unit; units | TEXT | yes | NA |
  | value | value | NUMERIC | no | |
- **History**: 1980-01

### natural_gas_consumption
- **API path**: natural-gas/cons/sum/data
- **API method**: route
- **Frequency**: monthly
- **Unique key**: (period, series)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | duoarea | duoarea; area | TEXT | yes | NA |
  | area_name | area-name; areaName; area_name | TEXT | no | |
  | process | process; processId | TEXT | yes | NA |
  | process_name | process-name; processName; process_name | TEXT | no | |
  | series | series; seriesId | TEXT | yes | NA |
  | series_description | series-description; seriesDescription; series_description | TEXT | no | |
  | value | value | NUMERIC | no | |
  | units | units; unit | TEXT | no | |
- **History**: 2001-01

### natural_gas_prices
- **API path**: natural-gas/pri/sum/data
- **API method**: route
- **Frequency**: monthly
- **Unique key**: (period, series)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | duoarea | duoarea; area | TEXT | yes | NA |
  | area_name | area-name; areaName; area_name | TEXT | no | |
  | process | process; processId | TEXT | yes | NA |
  | process_name | process-name; processName; process_name | TEXT | no | |
  | series | series; seriesId | TEXT | yes | NA |
  | series_description | series-description; seriesDescription; series_description | TEXT | no | |
  | value | value | NUMERIC | no | |
  | units | units; unit | TEXT | no | |
- **History**: 2001-01

### natural_gas_production
- **API path**: natural-gas/prod/sum/data
- **API method**: route
- **Frequency**: monthly
- **Unique key**: (period, series)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | duoarea | duoarea; area | TEXT | yes | NA |
  | area_name | area-name; areaName; area_name | TEXT | no | |
  | process | process; processId | TEXT | yes | NA |
  | process_name | process-name; processName; process_name | TEXT | no | |
  | series | series; seriesId | TEXT | yes | NA |
  | series_description | series-description; seriesDescription; series_description | TEXT | no | |
  | value | value | NUMERIC | no | |
  | units | units; unit | TEXT | no | |
- **History**: 2001-01

### natural_gas_storage
- **API path**: natural-gas/stor/sum/data
- **API method**: route
- **Frequency**: monthly
- **Unique key**: (period, series)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | duoarea | duoarea; area | TEXT | yes | NA |
  | area_name | area-name; areaName; area_name | TEXT | no | |
  | process | process; processId | TEXT | yes | NA |
  | process_name | process-name; processName; process_name | TEXT | no | |
  | series | series; seriesId | TEXT | yes | NA |
  | series_description | series-description; seriesDescription; series_description | TEXT | no | |
  | value | value | NUMERIC | no | |
  | units | units; unit | TEXT | no | |
- **History**: 2001-01

### nuclear_outages_facility
- **API path**: nuclear-outages/facility-nuclear-outages/data
- **API method**: route
- **Frequency**: daily
- **Unique key**: (period, facility_id, unit_id)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | facility_id | facilityId; facility_id; plantId | TEXT | yes | UNK |
  | facility_name | facilityName; facility_name; plantName | TEXT | no | |
  | unit_id | unitId; unit_id; generatorId | TEXT | yes | UNK |
  | unit_name | unitName; unit_name | TEXT | no | |
  | capacity_mw | capacity; capacity-mw; capacity_mw | NUMERIC | no | |
  | outage_mw | outage; outage-mw; outage_mw | NUMERIC | no | |
- **History**: 2018-01

### nuclear_outages_us
- **API path**: nuclear-outages/us-nuclear-outages/data
- **API method**: route
- **Frequency**: daily
- **Unique key**: (period)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | capacity_mw | capacity; capacity-mw; capacity_mw | NUMERIC | no | |
  | outage_mw | outage; outage-mw; outage_mw | NUMERIC | no | |
  | operating_mw | operating; operating-mw; operating_mw | NUMERIC | no | |
  | percent_outage | percentOutage; percent-outage; percent_outage | NUMERIC | no | |
- **History**: 2018-01

### operating_generator_capacity
- **API path**: /electricity/operating-generator-capacity/data
- **API method**: electricity
- **Frequency**: monthly
- **Unique key**: (period, plantid, generatorid)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | plantid | plantid | TEXT | yes | |
  | generatorid | generatorid | TEXT | yes | |
  | stateid | stateid | TEXT | no | |
  | entity_id | entity-id; entity_id | TEXT | no | |
  | entity_name | entity-name; entity_name | TEXT | no | |
  | energy_source_code | energy-source-code; energy_source_code | TEXT | no | |
  | prime_mover_code | prime-mover-code; prime_mover_code | TEXT | no | |
  | nameplate_capacity_mw | nameplate-capacity-mw; nameplate_capacity_mw | NUMERIC | no | |
  | net_summer_capacity_mw | net-summer-capacity-mw; net_summer_capacity_mw | NUMERIC | no | |
  | net_winter_capacity_mw | net-winter-capacity-mw; net_winter_capacity_mw | NUMERIC | no | |
  | operating_year | operating-year; operating_year | TEXT | no | |
  | technology | technology | TEXT | no | |
- **History**: 2001-01

### petroleum_prices
- **API path**: petroleum/pri/gnd/data
- **API method**: route
- **Frequency**: daily
- **Unique key**: (period, series)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | duoarea | duoarea; area | TEXT | yes | NA |
  | area_name | area-name; areaName; area_name | TEXT | no | |
  | product | product; productId | TEXT | yes | NA |
  | product_name | product-name; productName; product_name | TEXT | no | |
  | process | process; processId | TEXT | yes | NA |
  | process_name | process-name; processName; process_name | TEXT | no | |
  | series | series; seriesId | TEXT | yes | NA |
  | series_description | series-description; seriesDescription; series_description | TEXT | no | |
  | value | value | NUMERIC | no | |
  | units | units; unit | TEXT | no | |
- **History**: 1990-01

### petroleum_supply
- **API path**: petroleum/sum/snd/data
- **API method**: route
- **Frequency**: monthly
- **Unique key**: (period, series)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | duoarea | duoarea; area | TEXT | yes | NA |
  | area_name | area-name; areaName; area_name | TEXT | no | |
  | product | product; productId | TEXT | yes | NA |
  | product_name | product-name; productName; product_name | TEXT | no | |
  | process | process; processId | TEXT | yes | NA |
  | process_name | process-name; processName; process_name | TEXT | no | |
  | series | series; seriesId | TEXT | yes | NA |
  | series_description | series-description; seriesDescription; series_description | TEXT | no | |
  | value | value | NUMERIC | no | |
  | units | units; unit | TEXT | no | |
- **History**: 2001-01

### retail_sales
- **API path**: /electricity/retail-sales/data
- **API method**: electricity
- **Frequency**: monthly
- **Unique key**: (period, stateid, sectorid)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | stateid | stateid | TEXT | yes | |
  | sectorid | sectorid | TEXT | yes | |
  | revenue | revenue | NUMERIC | no | |
  | sales | sales | NUMERIC | no | |
  | price | price | NUMERIC | no | |
  | customers | customers | NUMERIC | no | |
- **History**: 2001-01

### rto_daily_region_data
- **API path**: /electricity/rto/daily-region-data/data
- **API method**: electricity
- **Frequency**: daily
- **Unique key**: (period, respondent, type)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | respondent | respondent | TEXT | yes | |
  | respondent_name | respondent-name; respondent_name | TEXT | no | |
  | type | type | TEXT | yes | |
  | type_name | type-name; type_name | TEXT | no | |
  | value | value | NUMERIC | no | |
  | value_units | value-units; value_units | TEXT | no | |
- **History**: 2018-01

### rto_fuel_type_data
- **API path**: /electricity/rto/fuel-type-data/data
- **API method**: electricity
- **Frequency**: hourly
- **Unique key**: (period, respondent, fueltype)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | TEXT | yes | |
  | respondent | respondent | TEXT | yes | |
  | respondent_name | respondent-name; respondent_name | TEXT | no | |
  | fueltype | fueltype | TEXT | yes | |
  | type_name | type-name; type_name | TEXT | no | |
  | value | value | NUMERIC | no | |
  | value_units | value-units; value_units | TEXT | no | |
- **History**: 2018-07

### rto_interchange_data
- **API path**: /electricity/rto/interchange-data/data
- **API method**: electricity
- **Frequency**: hourly
- **Unique key**: (period, fromba, toba)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | TEXT | yes | |
  | fromba | fromba | TEXT | yes | |
  | fromba_name | fromba-name; fromba_name | TEXT | no | |
  | toba | toba | TEXT | yes | |
  | toba_name | toba-name; toba_name | TEXT | no | |
  | value | value | NUMERIC | no | |
  | value_units | value-units; value_units | TEXT | no | |
- **History**: 2018-07

### rto_region_data
- **API path**: /electricity/rto/region-data/data
- **API method**: electricity
- **Frequency**: hourly
- **Unique key**: (period, respondent, type)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | TEXT | yes | |
  | respondent | respondent | TEXT | yes | |
  | respondent_name | respondent-name; respondent_name | TEXT | no | |
  | type | type | TEXT | yes | |
  | type_name | type-name; type_name | TEXT | no | |
  | value | value | NUMERIC | no | |
  | value_units | value-units; value_units | TEXT | no | |
- **History**: 2018-07

### rto_region_sub_ba_data
- **API path**: /electricity/rto/region-sub-ba-data/data
- **API method**: electricity
- **Frequency**: hourly
- **Unique key**: (period, subba, parent)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | TEXT | yes | |
  | subba | subba | TEXT | yes | |
  | subba_name | subba-name; subba_name | TEXT | no | |
  | parent | parent | TEXT | yes | |
  | parent_name | parent-name; parent_name | TEXT | no | |
  | value | value | NUMERIC | no | |
  | value_units | value-units; value_units | TEXT | no | |
- **History**: 2018-07

### seds
- **API path**: seds/data
- **API method**: route
- **Frequency**: annual
- **Extra API params**: frequency=annual
- **Unique key**: (period, msn, state_id)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | msn | msn; seriesId; series | TEXT | yes | NA |
  | state_id | stateId; state_id; stateid | TEXT | yes | US |
  | state_description | stateDescription; state_description | TEXT | no | |
  | value | value | NUMERIC | no | |
  | unit | unit; units | TEXT | no | |
- **History**: 1960-01

### sep_capability
- **API path**: /electricity/state-electricity-profiles/capability/data
- **API method**: electricity
- **Frequency**: annual
- **Extra API params**: frequency=annual
- **Unique key**: (period, stateid, fueltypeid)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | stateid | stateid; stateId | TEXT | yes | |
  | state_description | stateDescription; state_description | TEXT | no | |
  | fueltypeid | fueltypeid; fuelTypeId; energysourceid | TEXT | yes | |
  | fuel_type_description | fuelTypeDescription; fuel_type_description | TEXT | no | |
  | nameplate_capacity | capability; nameplate-capacity-mw; nameplatecapacity | NUMERIC | no | |
  | net_summer_capacity | net_summer_capacity | NUMERIC | no | |
  | net_winter_capacity | net_winter_capacity | NUMERIC | no | |
  | capacity_units | capacity-units | TEXT | no | megawatts |
- **History**: 1990-01

### sep_emissions
- **API path**: /electricity/state-electricity-profiles/emissions-by-state-by-fuel/data
- **API method**: electricity
- **Frequency**: annual
- **Extra API params**: frequency=annual
- **Unique key**: (period, stateid, sectorid, fuel_id)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | stateid | stateid; stateId | TEXT | yes | |
  | state_description | stateDescription; state_description | TEXT | no | |
  | sectorid | sectorid; sectorId | TEXT | yes | |
  | sector_description | sectorDescription; sector_description | TEXT | no | |
  | fuel_id | fuelid; fuelId; fuel_id | TEXT | yes | |
  | fuel_description | fuelDescription; fuel_description | TEXT | no | |
  | co2 | co2-thousand-metric-tons; co2 | NUMERIC | no | |
  | so2 | so2-short-tons; so2 | NUMERIC | no | |
  | nox | nox-short-tons; nox | NUMERIC | no | |
  | value_units | co2-thousand-metric-tons-units; co2-units; value_units | TEXT | no | |
- **History**: 1990-01

### sep_net_metering
- **API path**: /electricity/state-electricity-profiles/net-metering/data
- **API method**: electricity
- **Frequency**: annual
- **Extra API params**: frequency=annual
- **Unique key**: (period, stateid, sectorid)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | stateid | stateid; stateId | TEXT | yes | |
  | state_description | stateDescription; state_description | TEXT | no | |
  | sectorid | sectorid; sectorId | TEXT | yes | |
  | sector_description | sectorDescription; sector_description | TEXT | no | |
  | customers | customers | NUMERIC | no | |
  | capacity | capacity; nameplate-capacity | NUMERIC | no | |
  | generation | generation | NUMERIC | no | |
- **History**: 2010-01

### state_source_disposition
- **API path**: /electricity/state-electricity-profiles/source-disposition/data
- **API method**: electricity
- **Frequency**: monthly
- **Unique key**: (period, stateid)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | stateid | stateid; state | TEXT | yes | |
  | total_net_generation | total-net-generation; total_net_generation | NUMERIC | no | |
  | total_international_imports | total-international-imports; total_international_imports | NUMERIC | no | |
  | total_international_exports | total-international-exports; total_international_exports | NUMERIC | no | |
  | net_interstate_trade | net-interstate-trade; net_interstate_trade | NUMERIC | no | |
  | total_supply | total-supply; total_supply | NUMERIC | no | |
  | total_disposition | total-disposition; total_disposition | NUMERIC | no | |
  | estimated_losses | estimated-losses; estimated_losses | NUMERIC | no | |
- **History**: 2001-01

### state_summary
- **API path**: /electricity/state-electricity-profiles/summary/data
- **API method**: electricity
- **Frequency**: annual
- **Extra API params**: frequency=annual
- **Unique key**: (period, stateid)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | stateid | stateid; stateId; state | TEXT | yes | |
  | average_retail_price | average-retail-price; average_retail_price | NUMERIC | no | |
  | total_generation | net-generation; total-generation; total_generation | NUMERIC | no | |
  | total_consumption | total-retail-sales; total-consumption; total_consumption | NUMERIC | no | |
- **History**: 2001-01

### steo
- **API path**: steo/data
- **API method**: route
- **Frequency**: monthly
- **Unique key**: (period, series_id)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | series_id | seriesId; series_id; series; msn | TEXT | yes | NA |
  | series_description | seriesDescription; series-description; series_description | TEXT | no | |
  | value | value | NUMERIC | no | |
  | unit | unit; units | TEXT | no | |
- **History**: 2010-01

### total_energy
- **API path**: total-energy/data
- **API method**: route
- **Frequency**: monthly
- **Unique key**: (period, msn)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | msn | msn; seriesId; series | TEXT | yes | NA |
  | series_description | seriesDescription; series-description; series_description | TEXT | no | |
  | value | value | NUMERIC | no | |
  | unit | unit; units | TEXT | no | |
- **History**: 1973-01
