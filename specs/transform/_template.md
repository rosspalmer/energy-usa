# <Domain Name> Domain Model

## <schema>.<table_name>
<Plain-English description of what this table represents.>

- **Source tables**: eia.table_a, eia.table_b
- **Grain**: state + month
- **Join logic**: Match on stateid + period
- **Output columns**:
  | Column | Source | Logic |
  |--------|--------|-------|
  | state | eia.table_a.stateid | direct |
  | period | eia.table_a.period | direct |
  | derived_col | derived | col_a / col_b |
- **Unique key**: (state, period)
