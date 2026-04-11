"""Unit tests for generators.parse_spec.

Tests use two inline markdown fixtures (MINIMAL_SPEC and MULTI_DATASET_SPEC)
plus a tmp_path test for the file-based entry point.  Each test function
covers one well-defined behaviour so failures are easy to trace back to the
relevant parser code path.
"""

import pytest
from pathlib import Path

from energy_usa.generators.parse_spec import parse_spec, parse_spec_text
from energy_usa.generators.models import SourceSpec, DatasetSpec, ColumnSpec, FilterSpec


# ── Fixtures ──────────────────────────────────────────────────────────────────

MINIMAL_SPEC = """\
# EIA — U.S. Energy Information Administration

## Source
- **Type**: rest-json
- **Base URL**: https://api.eia.gov/v2
- **Auth**: API key via query param `api_key`, env var `EIA_API_KEY`
- **Pagination**: offset-based, `offset` + `length` params, response `total` field
- **Rate limit**: 4 concurrent requests, 500ms page delay

## Datasets

### retail_sales
- **API path**: /electricity/retail-sales
- **API method**: electricity
- **Frequency**: monthly
- **Unique key**: (period, stateid, sectorid)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | stateid | stateid | TEXT | yes | |
  | sectorid | sectorid | TEXT | yes | |
  | sales | sales | NUMERIC | no | |
  | revenue | revenue | NUMERIC | no | |
  | price | price | NUMERIC | no | |
  | customers | customers | NUMERIC | no | |
- **Filters**: Skip rows where stateid = 'US'
- **History**: 2001-01
"""

MULTI_DATASET_SPEC = """\
# EIA — U.S. Energy Information Administration

## Source
- **Type**: rest-json
- **Base URL**: https://api.eia.gov/v2
- **Auth**: API key via query param `api_key`, env var `EIA_API_KEY`
- **Pagination**: offset-based, `offset` + `length` params, response `total` field
- **Rate limit**: 4 concurrent requests, 500ms page delay

## Datasets

### retail_sales
- **API path**: /electricity/retail-sales
- **API method**: electricity
- **Frequency**: monthly
- **Unique key**: (period, stateid, sectorid)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | stateid | stateId; state_id; stateid | TEXT | yes | |
  | sectorid | sectorid | TEXT | yes | |
  | sales | sales | NUMERIC | no | |
- **Filters**: Skip rows where stateid = 'US'
- **History**: 2001-01

### co2_emissions
- **API path**: co2-emissions/co2-emissions-aggregates/data
- **API method**: route
- **Frequency**: annual
- **Unique key**: (period, stateid)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | stateid | stateId; state-id | TEXT | yes | XX |
  | value | value | NUMERIC | no | |
- **Extra API params**: frequency=annual, facets=stateid
- **Filters**: Skip rows where stateid = 'US'
- **History**: 1980-01
"""


# ── Source metadata ───────────────────────────────────────────────────────────


class TestParseSourceMetadata:
    def test_source_name(self):
        src = parse_spec_text(MINIMAL_SPEC)
        assert src.name == "eia"

    def test_base_url(self):
        src = parse_spec_text(MINIMAL_SPEC)
        assert src.base_url == "https://api.eia.gov/v2"

    def test_api_key_env(self):
        src = parse_spec_text(MINIMAL_SPEC)
        assert src.api_key_env == "EIA_API_KEY"

    def test_max_concurrent(self):
        src = parse_spec_text(MINIMAL_SPEC)
        assert src.max_concurrent == 4

    def test_page_delay(self):
        src = parse_spec_text(MINIMAL_SPEC)
        assert src.page_delay == pytest.approx(0.5)

    def test_returns_source_spec_instance(self):
        src = parse_spec_text(MINIMAL_SPEC)
        assert isinstance(src, SourceSpec)


# ── Single dataset ────────────────────────────────────────────────────────────


class TestParseSingleDataset:
    def setup_method(self):
        self.src = parse_spec_text(MINIMAL_SPEC)
        self.ds = self.src.datasets[0]

    def test_dataset_name(self):
        assert self.ds.name == "retail_sales"

    def test_api_path(self):
        assert self.ds.api_path == "/electricity/retail-sales"

    def test_api_method(self):
        assert self.ds.api_method == "electricity"

    def test_frequency(self):
        assert self.ds.frequency == "monthly"

    def test_unique_key(self):
        assert self.ds.unique_key == ("period", "stateid", "sectorid")

    def test_history_start(self):
        assert self.ds.history_start == "2001-01"

    def test_is_dataset_spec_instance(self):
        assert isinstance(self.ds, DatasetSpec)


# ── Column parsing ────────────────────────────────────────────────────────────


class TestParseColumns:
    def setup_method(self):
        self.src = parse_spec_text(MINIMAL_SPEC)
        self.ds = self.src.datasets[0]

    def test_column_count(self):
        assert len(self.ds.columns) == 7

    def test_first_column_name(self):
        assert self.ds.columns[0].name == "period"

    def test_first_column_api_field(self):
        assert self.ds.columns[0].api_field == "period"

    def test_first_column_pg_type(self):
        assert self.ds.columns[0].pg_type == "DATE"

    def test_first_column_required(self):
        assert self.ds.columns[0].required is True

    def test_numeric_column_not_required(self):
        sales_col = next(c for c in self.ds.columns if c.name == "sales")
        assert sales_col.required is False

    def test_numeric_column_type(self):
        sales_col = next(c for c in self.ds.columns if c.name == "sales")
        assert sales_col.pg_type == "NUMERIC"

    def test_column_is_column_spec_instance(self):
        assert isinstance(self.ds.columns[0], ColumnSpec)


# ── Filter parsing ────────────────────────────────────────────────────────────


class TestParseFilters:
    def setup_method(self):
        self.src = parse_spec_text(MINIMAL_SPEC)
        self.ds = self.src.datasets[0]

    def test_filter_count(self):
        assert len(self.ds.filters) == 1

    def test_filter_field(self):
        assert self.ds.filters[0].field == "stateid"

    def test_filter_operator(self):
        assert self.ds.filters[0].operator == "="

    def test_filter_value(self):
        assert self.ds.filters[0].value == "US"

    def test_filter_is_filter_spec_instance(self):
        assert isinstance(self.ds.filters[0], FilterSpec)


# ── Multiple datasets ─────────────────────────────────────────────────────────


class TestParseMultipleDatasets:
    def setup_method(self):
        self.src = parse_spec_text(MULTI_DATASET_SPEC)

    def test_dataset_count(self):
        assert len(self.src.datasets) == 2

    def test_first_dataset_name(self):
        assert self.src.datasets[0].name == "retail_sales"

    def test_second_dataset_name(self):
        assert self.src.datasets[1].name == "co2_emissions"

    def test_get_dataset_by_name(self):
        ds = self.src.get_dataset("co2_emissions")
        assert ds is not None
        assert ds.name == "co2_emissions"

    def test_second_dataset_api_path(self):
        ds = self.src.get_dataset("co2_emissions")
        assert ds.api_path == "co2-emissions/co2-emissions-aggregates/data"

    def test_second_dataset_api_method(self):
        ds = self.src.get_dataset("co2_emissions")
        assert ds.api_method == "route"

    def test_second_dataset_unique_key(self):
        ds = self.src.get_dataset("co2_emissions")
        assert ds.unique_key == ("period", "stateid")

    def test_second_dataset_history_start(self):
        ds = self.src.get_dataset("co2_emissions")
        assert ds.history_start == "1980-01"


# ── API aliases and defaults ──────────────────────────────────────────────────


class TestParseAliasesAndDefaults:
    def setup_method(self):
        self.src = parse_spec_text(MULTI_DATASET_SPEC)

    def test_retail_sales_stateid_api_field(self):
        ds = self.src.get_dataset("retail_sales")
        stateid_col = next(c for c in ds.columns if c.name == "stateid")
        assert stateid_col.api_field == "stateId"

    def test_retail_sales_stateid_aliases(self):
        ds = self.src.get_dataset("retail_sales")
        stateid_col = next(c for c in ds.columns if c.name == "stateid")
        assert stateid_col.api_aliases == ["state_id", "stateid"]

    def test_retail_sales_stateid_all_api_fields(self):
        ds = self.src.get_dataset("retail_sales")
        stateid_col = next(c for c in ds.columns if c.name == "stateid")
        assert stateid_col.all_api_fields == ["stateId", "state_id", "stateid"]

    def test_co2_stateid_default(self):
        ds = self.src.get_dataset("co2_emissions")
        stateid_col = next(c for c in ds.columns if c.name == "stateid")
        assert stateid_col.default == "XX"

    def test_co2_stateid_aliases(self):
        ds = self.src.get_dataset("co2_emissions")
        stateid_col = next(c for c in ds.columns if c.name == "stateid")
        assert stateid_col.api_aliases == ["state-id"]

    def test_no_aliases_gives_empty_list(self):
        ds = self.src.get_dataset("retail_sales")
        period_col = next(c for c in ds.columns if c.name == "period")
        assert period_col.api_aliases == []

    def test_no_default_gives_none(self):
        ds = self.src.get_dataset("retail_sales")
        period_col = next(c for c in ds.columns if c.name == "period")
        assert period_col.default is None


# ── Annual frequency → period_type / uses_year_only_dates ────────────────────


class TestParseAnnualFrequency:
    def setup_method(self):
        self.src = parse_spec_text(MULTI_DATASET_SPEC)
        self.ds = self.src.get_dataset("co2_emissions")

    def test_frequency_stored_as_annual(self):
        assert self.ds.frequency == "annual"

    def test_period_type_is_yearly(self):
        assert self.ds.period_type == "yearly"

    def test_uses_year_only_dates_true(self):
        assert self.ds.uses_year_only_dates is True

    def test_monthly_period_type_unchanged(self):
        monthly_ds = self.src.get_dataset("retail_sales")
        assert monthly_ds.period_type == "monthly"

    def test_monthly_uses_year_only_dates_false(self):
        monthly_ds = self.src.get_dataset("retail_sales")
        assert monthly_ds.uses_year_only_dates is False


# ── Extra API params ──────────────────────────────────────────────────────────


class TestParseExtraApiParams:
    def setup_method(self):
        self.src = parse_spec_text(MULTI_DATASET_SPEC)

    def test_co2_extra_params_frequency(self):
        ds = self.src.get_dataset("co2_emissions")
        assert ds.extra_api_params.get("frequency") == "annual"

    def test_co2_extra_params_facets(self):
        ds = self.src.get_dataset("co2_emissions")
        assert ds.extra_api_params.get("facets") == "stateid"

    def test_retail_sales_no_extra_params(self):
        ds = self.src.get_dataset("retail_sales")
        assert ds.extra_api_params == {}


# ── Parse from file (tmp_path) ────────────────────────────────────────────────


class TestParseFromFile:
    def test_parse_spec_path(self, tmp_path: Path):
        spec_file = tmp_path / "eia.md"
        spec_file.write_text(MINIMAL_SPEC, encoding="utf-8")
        src = parse_spec(spec_file)
        assert src.name == "eia"
        assert len(src.datasets) == 1
        assert src.datasets[0].name == "retail_sales"

    def test_parse_spec_preserves_all_columns(self, tmp_path: Path):
        spec_file = tmp_path / "eia.md"
        spec_file.write_text(MINIMAL_SPEC, encoding="utf-8")
        src = parse_spec(spec_file)
        ds = src.datasets[0]
        col_names = [c.name for c in ds.columns]
        assert col_names == ["period", "stateid", "sectorid", "sales", "revenue", "price", "customers"]

    def test_parse_spec_multi_dataset_from_file(self, tmp_path: Path):
        spec_file = tmp_path / "eia_multi.md"
        spec_file.write_text(MULTI_DATASET_SPEC, encoding="utf-8")
        src = parse_spec(spec_file)
        assert len(src.datasets) == 2

    def test_file_not_found_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            parse_spec(tmp_path / "nonexistent.md")
