"""Unit tests for generators.validate — Jinja2 template rendering.

Tests verify that the generated SQL contains the correct INSERT statements,
rule IDs, and ON CONFLICT DO UPDATE clauses.
"""

from __future__ import annotations

import textwrap

import pytest

from energy_usa.generators.parse_validate import parse_validate_spec
from energy_usa.generators.validate import generate_validate


# ---------------------------------------------------------------------------
# Shared spec
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
def spec():
    return parse_validate_spec(SPEC)


@pytest.fixture
def sql(spec, tmp_path) -> str:
    """Generate the audit_rules.sql and return its contents."""
    paths = generate_validate(spec, output_dir=tmp_path)
    assert len(paths) == 1
    return paths[0].read_text()


# ---------------------------------------------------------------------------
# File creation
# ---------------------------------------------------------------------------


class TestFileCreation:
    def test_returns_one_path(self, spec, tmp_path) -> None:
        paths = generate_validate(spec, output_dir=tmp_path)
        assert len(paths) == 1

    def test_output_path(self, spec, tmp_path) -> None:
        paths = generate_validate(spec, output_dir=tmp_path)
        expected = tmp_path / "docker/postgres/init/ingest/eia/audit_rules.sql"
        assert paths[0] == expected
        assert paths[0].exists()


# ---------------------------------------------------------------------------
# SQL content — structure
# ---------------------------------------------------------------------------


class TestSQLStructure:
    def test_insert_into_quality_audit_rules(self, sql: str) -> None:
        assert "INSERT INTO quality.audit_rules" in sql

    def test_on_conflict_rule_id(self, sql: str) -> None:
        assert "ON CONFLICT (rule_id) DO UPDATE SET" in sql

    def test_source_eia_present(self, sql: str) -> None:
        assert "'eia'" in sql


# ---------------------------------------------------------------------------
# Null-rate rules
# ---------------------------------------------------------------------------


class TestNullRateRules:
    def test_revenue_null_rate_rule_id(self, sql: str) -> None:
        assert "eia.retail_sales.null_rate.revenue" in sql

    def test_sales_null_rate_rule_id(self, sql: str) -> None:
        assert "eia.retail_sales.null_rate.sales" in sql

    def test_price_null_rate_rule_id(self, sql: str) -> None:
        assert "eia.retail_sales.null_rate.price" in sql

    def test_customers_null_rate_rule_id(self, sql: str) -> None:
        assert "eia.retail_sales.null_rate.customers" in sql

    def test_co2_null_rate_rule_id(self, sql: str) -> None:
        assert "eia.co2_emissions.null_rate.value" in sql

    def test_customers_threshold_value(self, sql: str) -> None:
        """Customers has max_null_pct=10, not 5."""
        # The threshold JSON should contain 10.0 near customers
        assert '"max_null_pct": 10.0' in sql or '"max_null_pct": 10' in sql


# ---------------------------------------------------------------------------
# Staleness rules
# ---------------------------------------------------------------------------


class TestStalenessRules:
    def test_retail_sales_staleness_rule_id(self, sql: str) -> None:
        assert "eia.retail_sales.staleness" in sql

    def test_co2_staleness_rule_id(self, sql: str) -> None:
        assert "eia.co2_emissions.staleness" in sql

    def test_retail_staleness_threshold_3_months(self, sql: str) -> None:
        assert '"max_months_behind": 3' in sql

    def test_co2_staleness_threshold_12_months(self, sql: str) -> None:
        assert '"max_months_behind": 12' in sql

    def test_staleness_column_null(self, sql: str) -> None:
        """Staleness checks have no column_name (table-level check)."""
        assert "NULL," in sql or "NULL\n" in sql


# ---------------------------------------------------------------------------
# Completeness rules
# ---------------------------------------------------------------------------


class TestCompletenessRules:
    def test_completeness_rule_id(self, sql: str) -> None:
        assert "eia.retail_sales.completeness" in sql

    def test_completeness_dimension_stateid(self, sql: str) -> None:
        assert '"stateid"' in sql

    def test_completeness_frequency_monthly(self, sql: str) -> None:
        assert '"monthly"' in sql

    def test_co2_no_completeness_rule(self, sql: str) -> None:
        """co2_emissions has no completeness spec, so no rule for it."""
        assert "eia.co2_emissions.completeness" not in sql


# ---------------------------------------------------------------------------
# Dataset without staleness (edge case)
# ---------------------------------------------------------------------------


class TestNoStaleness:
    def test_no_staleness_rule_when_zero_months(self, tmp_path) -> None:
        text = textwrap.dedent("""\
            # EIA Validation Rules

            ## simple_table
            - **Null tolerance**:
              | Column | Max null % |
              |--------|-----------|
              | value | 5 |
        """)
        spec = parse_validate_spec(text)
        paths = generate_validate(spec, output_dir=tmp_path)
        sql = paths[0].read_text()
        assert "staleness" not in sql
        assert "completeness" not in sql
        assert "eia.simple_table.null_rate.value" in sql
