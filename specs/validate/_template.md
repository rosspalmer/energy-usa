# <SOURCE_NAME> Validation Rules

## <dataset_name>
- **Date range**: YYYY-MM to present
- **Expected row count**: ~N rows/month
- **Null tolerance**:
  | Column | Max null % |
  |--------|-----------|
  | column_name | 5 |
- **Completeness**: Every state should have data for every month
- **Staleness**: Most recent period within 3 months of today
