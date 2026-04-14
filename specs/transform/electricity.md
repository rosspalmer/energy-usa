# Electricity Domain Model

## electricity.generation_mix
Combines generation data by fuel type with emissions data to show
the environmental profile of each state's electricity generation.

- **Source tables**: eia.state_source_disposition, eia.co2_emissions
- **Grain**: state, period
- **Join logic**: Match on stateid + period (year-level for CO2, month for generation)
- **Output columns**:
  | Column | Source | Logic | Type |
  |--------|--------|-------|------|
  | state | eia.state_source_disposition.stateid | direct | TEXT |
  | period | eia.state_source_disposition.period | direct | DATE |
  | total_generation_mwh | eia.state_source_disposition.generation | sum by state+period | NUMERIC |
  | co2_tons | eia.co2_emissions.value | sum where fuel=TO and sector=EC | NUMERIC |
  | carbon_intensity | derived | co2_tons / total_generation_mwh | NUMERIC |
- **Unique key**: (state, period)

## electricity.retail_by_state
State-level retail electricity sales aggregated across all sectors.

- **Source tables**: eia.retail_sales
- **Grain**: state, period
- **Join logic**: Single source, aggregate across sectorid
- **Output columns**:
  | Column | Source | Logic | Type |
  |--------|--------|-------|------|
  | state | eia.retail_sales.stateid | direct | TEXT |
  | period | eia.retail_sales.period | direct | DATE |
  | total_revenue | eia.retail_sales.revenue | sum by state+period | NUMERIC |
  | total_sales | eia.retail_sales.sales | sum by state+period | NUMERIC |
  | avg_price | derived | total_revenue / total_sales | NUMERIC |
  | total_customers | eia.retail_sales.customers | sum by state+period | NUMERIC |
- **Unique key**: (state, period)

## electricity.state_monthly_balance
Wide table giving each state's monthly electricity production by fuel type,
international/interstate trade, and consumption by retail sector.

- **Source tables**: eia.electric_power_operational, eia.state_source_disposition, eia.retail_sales
- **Grain**: state, period (month)
- **Join logic**: state_source_disposition is the anchor (one row per state+month).
  LEFT JOIN generation (pivoted from electric_power_operational WHERE sectorid='99')
  and consumption (pivoted from retail_sales) on (stateid, period).
- **Output columns**:
  | Column | Source | Logic | Type |
  |--------|--------|-------|------|
  | state | state_source_disposition.stateid | direct | TEXT |
  | period | state_source_disposition.period | direct | DATE |
  | gen_coal_mwh | electric_power_operational | SUM generation WHERE fueltypeid='COW', sectorid='99' | NUMERIC |
  | gen_natural_gas_mwh | electric_power_operational | SUM WHERE fueltypeid='NG' | NUMERIC |
  | gen_nuclear_mwh | electric_power_operational | SUM WHERE fueltypeid='NUC' | NUMERIC |
  | gen_hydro_mwh | electric_power_operational | SUM WHERE fueltypeid='HYC' | NUMERIC |
  | gen_solar_mwh | electric_power_operational | SUM WHERE fueltypeid='SUN' | NUMERIC |
  | gen_wind_mwh | electric_power_operational | SUM WHERE fueltypeid='WND' | NUMERIC |
  | gen_geothermal_mwh | electric_power_operational | SUM WHERE fueltypeid='GEO' | NUMERIC |
  | gen_biomass_mwh | electric_power_operational | SUM WHERE fueltypeid='BIO' | NUMERIC |
  | gen_petroleum_mwh | electric_power_operational | SUM WHERE fueltypeid IN ('PEL','PC') | NUMERIC |
  | gen_fossil_mwh | derived | coal + ng + petroleum | NUMERIC |
  | gen_renewable_mwh | derived | hydro + solar + wind + geo + biomass | NUMERIC |
  | gen_total_mwh | state_source_disposition.total_net_generation | direct | NUMERIC |
  | gen_other_mwh | derived | total - fossil - nuclear - renewable | NUMERIC |
  | international_imports_mwh | state_source_disposition.total_international_imports | direct | NUMERIC |
  | international_exports_mwh | state_source_disposition.total_international_exports | direct | NUMERIC |
  | net_interstate_trade_mwh | state_source_disposition.net_interstate_trade | direct | NUMERIC |
  | total_supply_mwh | state_source_disposition.total_supply | direct | NUMERIC |
  | consumption_residential_mwh | retail_sales | SUM sales WHERE sectorid='RES' | NUMERIC |
  | consumption_commercial_mwh | retail_sales | SUM sales WHERE sectorid='COM' | NUMERIC |
  | consumption_industrial_mwh | retail_sales | SUM sales WHERE sectorid='IND' | NUMERIC |
  | consumption_transportation_mwh | retail_sales | SUM sales WHERE sectorid='TRA' | NUMERIC |
  | consumption_other_mwh | retail_sales | SUM sales WHERE sectorid='OTH' | NUMERIC |
  | consumption_total_mwh | retail_sales | SUM sales WHERE sectorid='ALL' | NUMERIC |
  | estimated_losses_mwh | state_source_disposition.estimated_losses | direct | NUMERIC |
- **Unique key**: (state, period)
