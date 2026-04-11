# <SOURCE_NAME> — <Full Name of Data Source>

## Source
- **Type**: rest-json
- **Base URL**: https://api.example.gov/v2
- **Auth**: API key via query param `api_key`, env var `<SOURCE>_API_KEY`
- **Pagination**: offset-based, `offset` + `length` params, response `total` field
- **Rate limit**: 4 concurrent requests, 100ms page delay

## Datasets

### <dataset_name>
- **API path**: /category/subcategory/data
- **API method**: route
- **Frequency**: monthly
- **Unique key**: (period, stateid, sectorid)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | stateid | stateid | TEXT | yes | |
  | value | value | NUMERIC | no | |
- **Filters**: Skip rows where stateid = 'US'
- **History**: 2001-01
