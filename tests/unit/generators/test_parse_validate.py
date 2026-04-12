"""Unit tests for generators.parse_validate — markdown parsing.

Tests cover: source name extraction, dataset count, null tolerances,
staleness months, completeness dimensions, and date range parsing.
"""

from __future__ import annotations

import textwrap

import pytest

from energy_usa.generators.models_validate import (
    DatasetValidationSpec,
    NullToleranceSpec,
    ValidateSpec,
)
from energy_usa.generators.parse_validate import parse_validate_spec


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

SPEC = textwrap.dedent("""\
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

    ## co2_emissions
    - **Date range**: 1970-01 to present
    - **Null tolerance**:
      | Column | Max null % |
      |--------|-----------|
      | value | 2 |
    - **Staleness**: Most recent period within 12 months of today
""")


@pytest.fixture
def spec() -> ValidateSpec:
    return parse_validate_spec(SPEC)


# ---------------------------------------------------------------------------
# Top-level ValidateSpec
# ---------------------------------------------------------------------------


class TestValidateSpec:
    def test_source_name(self, spec: ValidateSpec) -> None:
        """Source name is the first word of the H1 heading, lowercased."""
        assert spec.source == "eia"

    def test_dataset_count(self, spec: ValidateSpec) -> None:
        assert len(spec.datasets) == 2

    def test_get_dataset_found(self, spec: ValidateSpec) -> None:
        ds = spec.get_dataset("retail_sales")
        assert ds is not None
        assert ds.name == "retail_sales"

    def test_get_dataset_not_found(self, spec: ValidateSpec) -> None:
        assert spec.get_dataset("nonexistent") is None

    def test_dataset_names(self, spec: ValidateSpec) -> None:
        names = [ds.name for ds in spec.datasets]
        assert names == ["retail_sales", "co2_emissions"]


# ---------------------------------------------------------------------------
# retail_sales dataset
# ---------------------------------------------------------------------------


class TestRetailSalesDataset:
    @pytest.fixture
    def ds(self, spec: ValidateSpec) -> DatasetValidationSpec:
        return spec.get_dataset("retail_sales")

    def test_date_range_start(self, ds: DatasetValidationSpec) -> None:
        assert ds.date_range_start == "2001-01"

    def test_expected_row_count_stored_raw(self, ds: DatasetValidationSpec) -> None:
        assert ds.expected_row_count == "~50 rows/month"

    def test_null_tolerance_count(self, ds: DatasetValidationSpec) -> None:
        assert len(ds.null_tolerances) == 4

    def test_null_tolerance_columns(self, ds: DatasetValidationSpec) -> None:
        cols = [nt.column for nt in ds.null_tolerances]
        assert cols == ["revenue", "sales", "price", "customers"]

    def test_null_tolerance_values(self, ds: DatasetValidationSpec) -> None:
        pcts = {nt.column: nt.max_null_pct for nt in ds.null_tolerances}
        assert pcts["revenue"] == 5.0
        assert pcts["customers"] == 10.0

    def test_completeness_dimensions(self, ds: DatasetValidationSpec) -> None:
        assert ds.completeness_dimensions == ["stateid"]

    def test_completeness_frequency(self, ds: DatasetValidationSpec) -> None:
        assert ds.completeness_frequency == "monthly"

    def test_staleness_months(self, ds: DatasetValidationSpec) -> None:
        assert ds.staleness_months == 3


# ---------------------------------------------------------------------------
# co2_emissions dataset
# ---------------------------------------------------------------------------


class TestCO2EmissionsDataset:
    @pytest.fixture
    def ds(self, spec: ValidateSpec) -> DatasetValidationSpec:
        return spec.get_dataset("co2_emissions")

    def test_date_range_start(self, ds: DatasetValidationSpec) -> None:
        assert ds.date_range_start == "1970-01"

    def test_null_tolerance_count(self, ds: DatasetValidationSpec) -> None:
        assert len(ds.null_tolerances) == 1

    def test_null_tolerance_column(self, ds: DatasetValidationSpec) -> None:
        assert ds.null_tolerances[0].column == "value"
        assert ds.null_tolerances[0].max_null_pct == 2.0

    def test_staleness_months(self, ds: DatasetValidationSpec) -> None:
        assert ds.staleness_months == 12

    def test_no_completeness_dimensions(self, ds: DatasetValidationSpec) -> None:
        assert ds.completeness_dimensions == []


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_no_h1_raises(self) -> None:
        with pytest.raises(ValueError, match="No H1 heading"):
            parse_validate_spec("## retail_sales\n- some content\n")

    def test_minimal_spec_no_error(self) -> None:
        text = textwrap.dedent("""\
            # EIA Validation Rules

            ## simple_table
            - **Date range**: 2010-01 to present
        """)
        spec = parse_validate_spec(text)
        assert spec.source == "eia"
        assert len(spec.datasets) == 1
        assert spec.datasets[0].name == "simple_table"
        assert spec.datasets[0].staleness_months == 0
        assert spec.datasets[0].null_tolerances == []
        assert spec.datasets[0].completeness_dimensions == []

    def test_annual_frequency_normalised(self) -> None:
        text = textwrap.dedent("""\
            # EIA Validation Rules

            ## annual_table
            - **Completeness**: Every stateid should have data for every year
        """)
        spec = parse_validate_spec(text)
        ds = spec.datasets[0]
        assert ds.completeness_frequency == "annual"

    def test_source_name_from_multiword_heading(self) -> None:
        text = textwrap.dedent("""\
            # Natural Gas Validation Rules

            ## nat_gas_prices
            - **Date range**: 2000-01 to present
        """)
        spec = parse_validate_spec(text)
        assert spec.source == "natural"
