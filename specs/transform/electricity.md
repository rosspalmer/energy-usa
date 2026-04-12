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
