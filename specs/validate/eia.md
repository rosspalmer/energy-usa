# EIA Validation Rules

## retail_sales
- **Date range**: 2001-01 to present
- **Expected row count**: ~50 rows/month
- **Null tolerance**:
  | Column | Max null % |
  |--------|-----------|
  | revenue | 5 |
  | sales | 5 |
  | price | 5 |
  | customers | 10 |
- **Completeness**: Every stateid should have data for every month
- **Staleness**: Most recent period within 3 months of today

## electric_power_operational
- **Date range**: 2001-01 to present
- **Null tolerance**:
  | Column | Max null % |
  |--------|-----------|
  | generation | 10 |
  | total_consumption | 15 |
- **Completeness**: Every stateid should have data for every month
- **Staleness**: Most recent period within 3 months of today

## state_source_disposition
- **Date range**: 2001-01 to present
- **Null tolerance**:
  | Column | Max null % |
  |--------|-----------|
  | generation | 10 |
- **Staleness**: Most recent period within 3 months of today

## state_summary
- **Date range**: 2001-01 to present
- **Staleness**: Most recent period within 18 months of today

## co2_emissions
- **Date range**: 1970-01 to present
- **Null tolerance**:
  | Column | Max null % |
  |--------|-----------|
  | value | 2 |
- **Staleness**: Most recent period within 24 months of today

## natural_gas_prices
- **Date range**: 1997-01 to present
- **Null tolerance**:
  | Column | Max null % |
  |--------|-----------|
  | value | 5 |
- **Staleness**: Most recent period within 3 months of today

## petroleum_prices
- **Date range**: 1995-01 to present
- **Null tolerance**:
  | Column | Max null % |
  |--------|-----------|
  | value | 5 |
- **Staleness**: Most recent period within 3 months of today

## total_energy
- **Date range**: 1973-01 to present
- **Null tolerance**:
  | Column | Max null % |
  |--------|-----------|
  | value | 5 |
- **Staleness**: Most recent period within 6 months of today

## seds
- **Date range**: 1960-01 to present
- **Null tolerance**:
  | Column | Max null % |
  |--------|-----------|
  | value | 10 |
- **Staleness**: Most recent period within 24 months of today
