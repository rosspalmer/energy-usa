"""Unit tests for generators.parse_transform — markdown parsing.

Tests cover: domain name extraction, table count, table names, source_tables,
grain, columns (count and individual fields), unique_key, join_logic,
description text, and edge cases.
"""

from __future__ import annotations

import textwrap

import pytest

from energy_usa.generators.models_transform import (
    TransformColumnSpec,
    TransformSpec,
    TransformTableSpec,
)
from energy_usa.generators.parse_transform import parse_transform_spec


# ---------------------------------------------------------------------------
# Shared fixture — mirrors specs/transform/electricity.md
# ---------------------------------------------------------------------------

SPEC = textwrap.dedent("""\
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
""")


@pytest.fixture
def spec() -> TransformSpec:
    return parse_transform_spec(SPEC)


# ---------------------------------------------------------------------------
# Top-level TransformSpec
# ---------------------------------------------------------------------------


class TestTransformSpec:
    def test_domain_name(self, spec: TransformSpec) -> None:
        """Domain is the first word of the H1 heading, lowercased."""
        assert spec.domain == "electricity"

    def test_table_count(self, spec: TransformSpec) -> None:
        assert len(spec.tables) == 2

    def test_table_names(self, spec: TransformSpec) -> None:
        names = [t.name for t in spec.tables]
        assert names == ["generation_mix", "retail_by_state"]

    def test_get_table_found(self, spec: TransformSpec) -> None:
        t = spec.get_table("generation_mix")
        assert t is not None
        assert t.name == "generation_mix"

    def test_get_table_not_found(self, spec: TransformSpec) -> None:
        assert spec.get_table("nonexistent") is None


# ---------------------------------------------------------------------------
# generation_mix table
# ---------------------------------------------------------------------------


class TestGenerationMix:
    @pytest.fixture
    def table(self, spec: TransformSpec) -> TransformTableSpec:
        return spec.get_table("generation_mix")

    def test_source_tables(self, table: TransformTableSpec) -> None:
        assert table.source_tables == [
            "eia.state_source_disposition",
            "eia.co2_emissions",
        ]

    def test_grain(self, table: TransformTableSpec) -> None:
        assert table.grain == ["state", "period"]

    def test_join_logic_contains_expected_text(self, table: TransformTableSpec) -> None:
        assert "stateid" in table.join_logic
        assert "period" in table.join_logic

    def test_description_contains_expected_text(self, table: TransformTableSpec) -> None:
        assert "environmental" in table.description
        assert "fuel type" in table.description

    def test_column_count(self, table: TransformTableSpec) -> None:
        assert len(table.columns) == 5

    def test_column_names(self, table: TransformTableSpec) -> None:
        names = [c.name for c in table.columns]
        assert names == [
            "state",
            "period",
            "total_generation_mwh",
            "co2_tons",
            "carbon_intensity",
        ]

    def test_direct_column_source(self, table: TransformTableSpec) -> None:
        state_col = table.columns[0]
        assert state_col.source == "eia.state_source_disposition.stateid"
        assert state_col.logic == "direct"
        assert state_col.pg_type == "TEXT"

    def test_date_column_type(self, table: TransformTableSpec) -> None:
        period_col = table.columns[1]
        assert period_col.pg_type == "DATE"

    def test_derived_column(self, table: TransformTableSpec) -> None:
        ci_col = table.columns[4]
        assert ci_col.source == "derived"
        assert "total_generation_mwh" in ci_col.logic

    def test_unique_key(self, table: TransformTableSpec) -> None:
        assert table.unique_key == ("state", "period")


# ---------------------------------------------------------------------------
# retail_by_state table
# ---------------------------------------------------------------------------


class TestRetailByState:
    @pytest.fixture
    def table(self, spec: TransformSpec) -> TransformTableSpec:
        return spec.get_table("retail_by_state")

    def test_source_tables(self, table: TransformTableSpec) -> None:
        assert table.source_tables == ["eia.retail_sales"]

    def test_grain(self, table: TransformTableSpec) -> None:
        assert table.grain == ["state", "period"]

    def test_join_logic_contains_expected_text(self, table: TransformTableSpec) -> None:
        assert "sectorid" in table.join_logic

    def test_description_contains_expected_text(self, table: TransformTableSpec) -> None:
        assert "retail" in table.description.lower()
        assert "sector" in table.description.lower()

    def test_column_count(self, table: TransformTableSpec) -> None:
        assert len(table.columns) == 6

    def test_column_names(self, table: TransformTableSpec) -> None:
        names = [c.name for c in table.columns]
        assert names == [
            "state",
            "period",
            "total_revenue",
            "total_sales",
            "avg_price",
            "total_customers",
        ]

    def test_derived_avg_price(self, table: TransformTableSpec) -> None:
        avg_col = table.columns[4]
        assert avg_col.name == "avg_price"
        assert avg_col.source == "derived"
        assert "total_revenue" in avg_col.logic

    def test_unique_key(self, table: TransformTableSpec) -> None:
        assert table.unique_key == ("state", "period")

    def test_numeric_default_type(self, table: TransformTableSpec) -> None:
        """Columns without an explicit type should default to NUMERIC."""
        numeric_cols = [c for c in table.columns if c.pg_type == "NUMERIC"]
        assert len(numeric_cols) >= 4


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_no_h1_raises(self) -> None:
        with pytest.raises(ValueError, match="No H1 heading"):
            parse_transform_spec("## electricity.some_table\n- **Source tables**: foo\n")

    def test_minimal_spec_no_error(self) -> None:
        text = textwrap.dedent("""\
            # Electricity Domain Model

            ## electricity.simple_table
            A simple table with no join complexity.

            - **Source tables**: eia.retail_sales
            - **Grain**: state, period
            - **Join logic**: Single source
            - **Output columns**:
              | Column | Source | Logic | Type |
              |--------|--------|-------|------|
              | state | eia.retail_sales.stateid | direct | TEXT |
            - **Unique key**: (state, period)
        """)
        spec = parse_transform_spec(text)
        assert spec.domain == "electricity"
        assert len(spec.tables) == 1
        t = spec.tables[0]
        assert t.name == "simple_table"
        assert t.unique_key == ("state", "period")
        assert len(t.columns) == 1

    def test_domain_name_from_multiword_heading(self) -> None:
        text = textwrap.dedent("""\
            # Fossil Fuels Domain Model

            ## fossil_fuels.nat_gas_prices
            Prices for natural gas.

            - **Source tables**: eia.nat_gas
            - **Grain**: state, period
            - **Join logic**: Single source
            - **Output columns**:
              | Column | Source | Logic | Type |
              |--------|--------|-------|------|
              | state | eia.nat_gas.stateid | direct | TEXT |
            - **Unique key**: (state, period)
        """)
        spec = parse_transform_spec(text)
        assert spec.domain == "fossil"

    def test_table_name_without_schema_prefix(self) -> None:
        """H2 headings without a dot use the full heading as the table name."""
        text = textwrap.dedent("""\
            # Electricity Domain Model

            ## bare_table_name
            A table without a schema prefix.

            - **Source tables**: eia.retail_sales
            - **Grain**: state
            - **Join logic**: Direct
            - **Output columns**:
              | Column | Source | Logic | Type |
              |--------|--------|-------|------|
              | state | eia.retail_sales.stateid | direct | TEXT |
            - **Unique key**: (state)
        """)
        spec = parse_transform_spec(text)
        assert spec.tables[0].name == "bare_table_name"
