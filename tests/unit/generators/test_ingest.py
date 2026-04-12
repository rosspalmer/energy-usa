"""Unit tests for generators.ingest — Jinja2 template rendering.

Each test verifies one well-defined behaviour of the rendered output so that
template regressions are easy to locate.  Tests use an in-memory SourceSpec
built from a small inline spec string rather than touching the filesystem,
except for the ``tmp_path`` tests that verify actual file creation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from energy_usa.generators.ingest import generate_ingest
from energy_usa.generators.models import (
    ColumnSpec,
    DatasetSpec,
    FilterSpec,
    SourceSpec,
)
from energy_usa.generators.parse_spec import parse_spec_text


# ── Shared spec fixture ───────────────────────────────────────────────────────

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
  | revenue | revenue | NUMERIC | no | |
  | sales | sales | NUMERIC | no | |
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
  | stateid | stateid | TEXT | yes | |
  | sectorid | sectorid | TEXT | yes | |
  | revenue | revenue | NUMERIC | no | |
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
  | stateid | stateId; state_id; stateid | TEXT | yes | US |
  | value | value | NUMERIC | no | |
- **Extra API params**: frequency=annual
- **Filters**: Skip rows where stateid = 'US'
- **History**: 1980-01
"""


@pytest.fixture
def minimal_spec() -> SourceSpec:
    return parse_spec_text(MINIMAL_SPEC)


@pytest.fixture
def multi_spec() -> SourceSpec:
    return parse_spec_text(MULTI_DATASET_SPEC)


# ── SQL schema template ───────────────────────────────────────────────────────


class TestSchemaSQL:
    def test_table_name_in_output(self, minimal_spec, tmp_path):
        generate_ingest(minimal_spec, output_dir=tmp_path)
        sql_file = tmp_path / "docker/postgres/init/ingest/eia/retail_sales.sql"
        assert sql_file.exists()
        content = sql_file.read_text()
        assert "eia.retail_sales" in content

    def test_create_table_if_not_exists(self, minimal_spec, tmp_path):
        generate_ingest(minimal_spec, output_dir=tmp_path)
        content = (tmp_path / "docker/postgres/init/ingest/eia/retail_sales.sql").read_text()
        assert "CREATE TABLE IF NOT EXISTS" in content

    def test_primary_key_columns(self, minimal_spec, tmp_path):
        generate_ingest(minimal_spec, output_dir=tmp_path)
        content = (tmp_path / "docker/postgres/init/ingest/eia/retail_sales.sql").read_text()
        assert "PRIMARY KEY (period, stateid, sectorid)" in content

    def test_ingested_at_column_present(self, minimal_spec, tmp_path):
        generate_ingest(minimal_spec, output_dir=tmp_path)
        content = (tmp_path / "docker/postgres/init/ingest/eia/retail_sales.sql").read_text()
        assert "ingested_at TIMESTAMPTZ NOT NULL DEFAULT now()" in content

    def test_numeric_columns_present(self, minimal_spec, tmp_path):
        generate_ingest(minimal_spec, output_dir=tmp_path)
        content = (tmp_path / "docker/postgres/init/ingest/eia/retail_sales.sql").read_text()
        assert "revenue NUMERIC" in content
        assert "sales NUMERIC" in content

    def test_required_columns_have_not_null(self, minimal_spec, tmp_path):
        generate_ingest(minimal_spec, output_dir=tmp_path)
        content = (tmp_path / "docker/postgres/init/ingest/eia/retail_sales.sql").read_text()
        assert "period DATE NOT NULL" in content
        assert "stateid TEXT NOT NULL" in content

    def test_optional_columns_lack_not_null(self, minimal_spec, tmp_path):
        generate_ingest(minimal_spec, output_dir=tmp_path)
        content = (tmp_path / "docker/postgres/init/ingest/eia/retail_sales.sql").read_text()
        # revenue is optional; must not have NOT NULL
        lines = content.splitlines()
        revenue_lines = [l for l in lines if "revenue" in l and "NUMERIC" in l]
        assert revenue_lines, "revenue column not found"
        assert "NOT NULL" not in revenue_lines[0]

    def test_frequency_in_comment(self, minimal_spec, tmp_path):
        generate_ingest(minimal_spec, output_dir=tmp_path)
        content = (tmp_path / "docker/postgres/init/ingest/eia/retail_sales.sql").read_text()
        assert "monthly" in content


# ── DB upsert module template ─────────────────────────────────────────────────


class TestDBModule:
    def _get_db_content(self, spec, tmp_path, name="retail_sales"):
        generate_ingest(spec, output_dir=tmp_path)
        return (tmp_path / f"src/energy_usa/db/ingest/eia/{name}.py").read_text()

    def test_upsert_function_exists(self, minimal_spec, tmp_path):
        content = self._get_db_content(minimal_spec, tmp_path)
        assert "def upsert_retail_sales(" in content

    def test_insert_into_table(self, minimal_spec, tmp_path):
        content = self._get_db_content(minimal_spec, tmp_path)
        assert "INSERT INTO eia.retail_sales" in content

    def test_on_conflict_clause(self, minimal_spec, tmp_path):
        content = self._get_db_content(minimal_spec, tmp_path)
        assert "ON CONFLICT (period, stateid, sectorid)" in content

    def test_do_update_set(self, minimal_spec, tmp_path):
        content = self._get_db_content(minimal_spec, tmp_path)
        assert "DO UPDATE SET" in content

    def test_non_key_columns_in_update_set(self, minimal_spec, tmp_path):
        content = self._get_db_content(minimal_spec, tmp_path)
        assert "revenue = EXCLUDED.revenue" in content
        assert "sales = EXCLUDED.sales" in content

    def test_key_columns_not_in_update_set(self, minimal_spec, tmp_path):
        content = self._get_db_content(minimal_spec, tmp_path)
        # period should appear in INSERT but not in DO UPDATE SET
        # Find the DO UPDATE SET block
        do_update_idx = content.index("DO UPDATE SET")
        update_section = content[do_update_idx:]
        # stateid should not be updated
        assert "stateid = EXCLUDED" not in update_section

    def test_ingested_at_updated(self, minimal_spec, tmp_path):
        content = self._get_db_content(minimal_spec, tmp_path)
        assert "ingested_at = now()" in content

    def test_period_normalization_call(self, minimal_spec, tmp_path):
        content = self._get_db_content(minimal_spec, tmp_path)
        assert 'normalize_period(r.get("period"), "monthly")' in content

    def test_safe_numeric_imported_when_numeric_columns(self, minimal_spec, tmp_path):
        content = self._get_db_content(minimal_spec, tmp_path)
        assert "safe_numeric" in content
        assert "from energy_usa.db.period import normalize_period, safe_numeric" in content

    def test_psycopg_param_placeholders(self, minimal_spec, tmp_path):
        content = self._get_db_content(minimal_spec, tmp_path)
        assert "%(period)s" in content
        assert "%(revenue)s" in content

    def test_filter_skips_matching_rows(self, minimal_spec, tmp_path):
        content = self._get_db_content(minimal_spec, tmp_path)
        # Filter: stateid = 'US' → skip rows where stateid == "US"
        assert '"US"' in content or "'US'" in content
        assert "stateid" in content

    def test_annual_period_type_used(self, multi_spec, tmp_path):
        content = self._get_db_content(multi_spec, tmp_path, "co2_emissions")
        assert 'normalize_period(r.get("period"), "yearly")' in content

    def test_aliases_produce_fallback_chain(self, multi_spec, tmp_path):
        content = self._get_db_content(multi_spec, tmp_path, "co2_emissions")
        # co2 stateid has aliases: stateId; state_id; stateid
        assert 'r.get("stateId")' in content
        assert 'r.get("state_id")' in content
        assert 'r.get("stateid")' in content

    def test_default_value_appended(self, multi_spec, tmp_path):
        content = self._get_db_content(multi_spec, tmp_path, "co2_emissions")
        # co2 stateid has default "US"
        assert 'or "US"' in content

    def test_safe_numeric_not_imported_when_no_numeric_columns(self, tmp_path):
        """When a dataset has no NUMERIC columns, safe_numeric should not be imported."""
        spec = SourceSpec(
            name="eia",
            base_url="https://api.eia.gov/v2",
            api_key_env="EIA_API_KEY",
            max_concurrent=4,
            page_delay=0.5,
            datasets=[
                DatasetSpec(
                    name="text_only",
                    api_path="/some/path",
                    api_method="electricity",
                    frequency="monthly",
                    unique_key=("period", "stateid"),
                    columns=[
                        ColumnSpec("period", "period", "DATE", required=True),
                        ColumnSpec("stateid", "stateid", "TEXT", required=True),
                        ColumnSpec("label", "label", "TEXT", required=False),
                    ],
                    filters=[],
                    history_start="2001-01",
                )
            ],
        )
        generate_ingest(spec, output_dir=tmp_path)
        content = (tmp_path / "src/energy_usa/db/ingest/eia/text_only.py").read_text()
        assert "safe_numeric" not in content
        assert "from energy_usa.db.period import normalize_period" in content


# ── Flow module template ──────────────────────────────────────────────────────


class TestFlowModule:
    def _get_flow_content(self, spec, tmp_path, name="retail_sales"):
        generate_ingest(spec, output_dir=tmp_path)
        return (tmp_path / f"src/energy_usa/flows/ingest/eia/{name}.py").read_text()

    def test_async_flow_function_exists(self, minimal_spec, tmp_path):
        content = self._get_flow_content(minimal_spec, tmp_path)
        assert "async def ingest_eia_retail_sales(" in content

    def test_flow_decorator(self, minimal_spec, tmp_path):
        content = self._get_flow_content(minimal_spec, tmp_path)
        assert '@flow(' in content
        assert '"ingest-eia-retail-sales"' in content

    def test_fetch_task_async(self, minimal_spec, tmp_path):
        content = self._get_flow_content(minimal_spec, tmp_path)
        assert "async def fetch_eia_retail_sales(" in content

    def test_upsert_task_exists(self, minimal_spec, tmp_path):
        content = self._get_flow_content(minimal_spec, tmp_path)
        assert "def upsert_retail_sales_task(" in content

    def test_electricity_api_call(self, minimal_spec, tmp_path):
        content = self._get_flow_content(minimal_spec, tmp_path)
        assert "manager.get_electricity(" in content
        assert "retail-sales/data" in content

    def test_route_api_call_for_route_method(self, multi_spec, tmp_path):
        content = self._get_flow_content(multi_spec, tmp_path, "co2_emissions")
        assert "manager.get_route(" in content
        assert "EIA_CO2_EMISSIONS_PATH" in content

    def test_route_path_constant_defined(self, multi_spec, tmp_path):
        content = self._get_flow_content(multi_spec, tmp_path, "co2_emissions")
        assert 'EIA_CO2_EMISSIONS_PATH = "co2-emissions/co2-emissions-aggregates/data"' in content

    def test_data_columns_constant(self, minimal_spec, tmp_path):
        content = self._get_flow_content(minimal_spec, tmp_path)
        assert "EIA_RETAIL_SALES_COLUMNS" in content
        # Should contain the numeric column names
        assert "revenue" in content
        assert "sales" in content

    def test_year_only_dates_for_annual(self, multi_spec, tmp_path):
        content = self._get_flow_content(multi_spec, tmp_path, "co2_emissions")
        assert "start_year" in content
        assert "end_year" in content
        assert "start[:4]" in content

    def test_no_year_stripping_for_monthly(self, minimal_spec, tmp_path):
        content = self._get_flow_content(minimal_spec, tmp_path)
        assert "start_year" not in content

    def test_extra_api_params_in_flow(self, multi_spec, tmp_path):
        content = self._get_flow_content(multi_spec, tmp_path, "co2_emissions")
        assert '"frequency"' in content or "'frequency'" in content

    def test_settings_used(self, minimal_spec, tmp_path):
        content = self._get_flow_content(minimal_spec, tmp_path)
        assert "settings = Settings()" in content
        assert "settings.eia_api_key" in content
        assert "settings.ingest_database_url" in content

    def test_resolve_date_range_called(self, minimal_spec, tmp_path):
        content = self._get_flow_content(minimal_spec, tmp_path)
        assert "resolve_date_range(" in content

    def test_zero_rows_raises_runtime_error(self, minimal_spec, tmp_path):
        content = self._get_flow_content(minimal_spec, tmp_path)
        assert "RuntimeError" in content
        assert "Zero rows upserted" in content

    def test_correct_imports(self, minimal_spec, tmp_path):
        content = self._get_flow_content(minimal_spec, tmp_path)
        assert "from energy_usa.config import Settings" in content
        assert "from energy_usa.db.connection import get_connection" in content
        assert "from energy_usa.clients.eia import EIAManager" in content
        assert "from energy_usa.db.ingest.eia.retail_sales import upsert_retail_sales" in content


# ── Single dataset generation ─────────────────────────────────────────────────


class TestSingleDatasetGeneration:
    def test_only_requested_dataset_files_created(self, multi_spec, tmp_path):
        generate_ingest(multi_spec, output_dir=tmp_path, datasets=["retail_sales"])
        retail_sql = tmp_path / "docker/postgres/init/ingest/eia/retail_sales.sql"
        co2_sql = tmp_path / "docker/postgres/init/ingest/eia/co2_emissions.sql"
        assert retail_sql.exists()
        assert not co2_sql.exists()

    def test_single_dataset_returns_three_paths(self, minimal_spec, tmp_path):
        paths = generate_ingest(minimal_spec, output_dir=tmp_path, datasets=["retail_sales"])
        assert len(paths) == 3

    def test_all_datasets_generated_when_no_filter(self, multi_spec, tmp_path):
        paths = generate_ingest(multi_spec, output_dir=tmp_path)
        # 2 datasets × 3 files each = 6
        assert len(paths) == 6

    def test_empty_datasets_filter_generates_nothing(self, minimal_spec, tmp_path):
        paths = generate_ingest(minimal_spec, output_dir=tmp_path, datasets=[])
        assert paths == []

    def test_returned_paths_exist(self, minimal_spec, tmp_path):
        paths = generate_ingest(minimal_spec, output_dir=tmp_path)
        for p in paths:
            assert p.exists(), f"Expected generated file not found: {p}"
