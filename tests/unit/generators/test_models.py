"""Unit tests for generators.models dataclasses.

Each test function covers one behaviour in isolation so that a failure
clearly points to the broken model property rather than to the test fixture.
"""

import pytest

from energy_usa.generators.models import (
    ColumnSpec,
    DatasetSpec,
    FilterSpec,
    SourceSpec,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_column(
    name: str = "value",
    api_field: str = "value",
    pg_type: str = "NUMERIC",
    required: bool = False,
    api_aliases: list[str] | None = None,
    default: str | None = None,
) -> ColumnSpec:
    return ColumnSpec(
        name=name,
        api_field=api_field,
        pg_type=pg_type,
        required=required,
        api_aliases=api_aliases or [],
        default=default,
    )


def _make_dataset(
    name: str = "retail_sales",
    frequency: str = "monthly",
    columns: list[ColumnSpec] | None = None,
    unique_key: tuple[str, ...] = ("period", "stateid"),
    filters: list[FilterSpec] | None = None,
) -> DatasetSpec:
    if columns is None:
        columns = [
            _make_column("period", "period", "DATE", required=True),
            _make_column("stateid", "stateid", "TEXT", required=True),
            _make_column("sales", "sales", "NUMERIC"),
            _make_column("revenue", "revenue", "NUMERIC"),
            _make_column("label", "stateDescription", "TEXT"),
        ]
    return DatasetSpec(
        name=name,
        api_path="/electricity/retail-sales",
        api_method="electricity",
        frequency=frequency,
        unique_key=unique_key,
        columns=columns,
        filters=filters or [],
        history_start="2001-01",
    )


# ── ColumnSpec ────────────────────────────────────────────────────────────────


class TestColumnSpec:
    def test_required_flag_stored(self):
        col = _make_column(required=True)
        assert col.required is True

    def test_not_required_by_default(self):
        col = _make_column(required=False)
        assert col.required is False

    def test_aliases_and_default(self):
        col = ColumnSpec(
            name="stateid",
            api_field="stateId",
            pg_type="TEXT",
            required=True,
            api_aliases=["state_id", "stateid"],
            default="XX",
        )
        assert col.api_aliases == ["state_id", "stateid"]
        assert col.default == "XX"

    def test_default_is_none_when_omitted(self):
        col = _make_column()
        assert col.default is None

    def test_api_aliases_default_to_empty_list(self):
        col = _make_column()
        assert col.api_aliases == []

    def test_is_numeric_true_for_numeric_type(self):
        col = _make_column(pg_type="NUMERIC")
        assert col.is_numeric is True

    def test_is_numeric_case_insensitive(self):
        # Users might write "numeric" in a spec; ensure we handle that.
        col = _make_column(pg_type="numeric")
        assert col.is_numeric is True

    def test_is_numeric_false_for_text(self):
        col = _make_column(pg_type="TEXT")
        assert col.is_numeric is False

    def test_is_numeric_false_for_date(self):
        col = _make_column(pg_type="DATE")
        assert col.is_numeric is False

    def test_is_numeric_false_for_timestamptz(self):
        col = _make_column(pg_type="TIMESTAMPTZ")
        assert col.is_numeric is False

    def test_all_api_fields_no_aliases(self):
        col = _make_column(api_field="value")
        assert col.all_api_fields == ["value"]

    def test_all_api_fields_with_aliases(self):
        col = ColumnSpec(
            name="stateid",
            api_field="stateId",
            pg_type="TEXT",
            required=True,
            api_aliases=["state_id", "stateid"],
        )
        assert col.all_api_fields == ["stateId", "state_id", "stateid"]

    def test_all_api_fields_preserves_order(self):
        col = ColumnSpec(
            name="x",
            api_field="A",
            pg_type="TEXT",
            required=False,
            api_aliases=["B", "C", "D"],
        )
        assert col.all_api_fields == ["A", "B", "C", "D"]


# ── FilterSpec ────────────────────────────────────────────────────────────────


class TestFilterSpec:
    def test_basic_construction(self):
        f = FilterSpec(field="stateid", operator="=", value="US")
        assert f.field == "stateid"
        assert f.operator == "="
        assert f.value == "US"

    def test_fields_are_plain_strings(self):
        f = FilterSpec(field="sectorid", operator="=", value="99")
        assert isinstance(f.field, str)
        assert isinstance(f.operator, str)
        assert isinstance(f.value, str)


# ── DatasetSpec ───────────────────────────────────────────────────────────────


class TestDatasetSpec:
    def test_non_key_columns_excludes_key_columns(self):
        ds = _make_dataset(unique_key=("period", "stateid"))
        non_key_names = [c.name for c in ds.non_key_columns]
        assert "period" not in non_key_names
        assert "stateid" not in non_key_names

    def test_non_key_columns_includes_value_columns(self):
        ds = _make_dataset(unique_key=("period", "stateid"))
        non_key_names = [c.name for c in ds.non_key_columns]
        assert "sales" in non_key_names
        assert "revenue" in non_key_names
        assert "label" in non_key_names

    def test_non_key_columns_preserves_order(self):
        ds = _make_dataset(unique_key=("period", "stateid"))
        # Default columns order: period, stateid, sales, revenue, label
        # Non-key should be: sales, revenue, label (in that order)
        non_key_names = [c.name for c in ds.non_key_columns]
        assert non_key_names == ["sales", "revenue", "label"]

    def test_data_columns_are_numeric_non_key(self):
        ds = _make_dataset(unique_key=("period", "stateid"))
        data_col_names = [c.name for c in ds.data_columns]
        assert "sales" in data_col_names
        assert "revenue" in data_col_names

    def test_data_columns_excludes_text_non_key(self):
        ds = _make_dataset(unique_key=("period", "stateid"))
        data_col_names = [c.name for c in ds.data_columns]
        # 'label' is TEXT, not NUMERIC
        assert "label" not in data_col_names

    def test_data_columns_excludes_key_columns(self):
        ds = _make_dataset(unique_key=("period", "stateid"))
        data_col_names = [c.name for c in ds.data_columns]
        assert "period" not in data_col_names
        assert "stateid" not in data_col_names

    def test_period_type_monthly_passes_through(self):
        ds = _make_dataset(frequency="monthly")
        assert ds.period_type == "monthly"

    def test_period_type_annual_maps_to_yearly(self):
        ds = _make_dataset(frequency="annual")
        assert ds.period_type == "yearly"

    def test_period_type_quarterly_passes_through(self):
        ds = _make_dataset(frequency="quarterly")
        assert ds.period_type == "quarterly"

    def test_uses_year_only_dates_annual(self):
        ds = _make_dataset(frequency="annual")
        assert ds.uses_year_only_dates is True

    def test_uses_year_only_dates_monthly(self):
        ds = _make_dataset(frequency="monthly")
        assert ds.uses_year_only_dates is False

    def test_uses_year_only_dates_quarterly(self):
        ds = _make_dataset(frequency="quarterly")
        assert ds.uses_year_only_dates is False

    def test_extra_api_params_default_empty(self):
        ds = _make_dataset()
        assert ds.extra_api_params == {}

    def test_indexes_default_empty(self):
        ds = _make_dataset()
        assert ds.indexes == []

    def test_mutable_defaults_are_independent(self):
        """Two DatasetSpec instances must not share the same list objects."""
        ds1 = _make_dataset(name="a")
        ds2 = _make_dataset(name="b")
        ds1.indexes.append("stateid")
        assert ds2.indexes == []


# ── SourceSpec ────────────────────────────────────────────────────────────────


class TestSourceSpec:
    def _make_source(self, datasets: list[DatasetSpec] | None = None) -> SourceSpec:
        if datasets is None:
            datasets = [_make_dataset()]
        return SourceSpec(
            name="eia",
            base_url="https://api.eia.gov/v2",
            api_key_env="EIA_API_KEY",
            max_concurrent=4,
            page_delay=0.5,
            datasets=datasets,
        )

    def test_basic_construction(self):
        src = self._make_source()
        assert src.name == "eia"
        assert src.base_url == "https://api.eia.gov/v2"
        assert src.api_key_env == "EIA_API_KEY"
        assert src.max_concurrent == 4
        assert src.page_delay == 0.5

    def test_get_dataset_returns_correct_dataset(self):
        ds = _make_dataset(name="retail_sales")
        src = self._make_source(datasets=[ds])
        found = src.get_dataset("retail_sales")
        assert found is ds

    def test_get_dataset_returns_none_for_missing(self):
        src = self._make_source()
        assert src.get_dataset("nonexistent") is None

    def test_get_dataset_with_multiple_datasets(self):
        ds1 = _make_dataset(name="retail_sales")
        ds2 = _make_dataset(name="co2_emissions")
        src = self._make_source(datasets=[ds1, ds2])
        assert src.get_dataset("co2_emissions") is ds2
        assert src.get_dataset("retail_sales") is ds1

    def test_datasets_list_is_mutable(self):
        src = self._make_source(datasets=[])
        ds = _make_dataset()
        src.datasets.append(ds)
        assert len(src.datasets) == 1
