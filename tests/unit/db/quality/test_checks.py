"""Unit tests for energy_usa.db.quality.checks (no real DB required).

Each check function is tested by mocking the psycopg cursor's fetchone /
fetchall return values.  The spec tests listed in the task are all covered,
plus a small number of edge-case tests where the behaviour is unambiguous.
"""

from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest

from energy_usa.db.quality.audit import AuditRule, AuditResult
from energy_usa.db.quality.checks import (
    check_completeness,
    check_null_rate,
    check_range,
    check_row_count,
    check_staleness,
    run_check,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_conn(fetchone_return=None, fetchall_return=None):
    """Return (conn, cur) where cur is a MagicMock with preset return values."""
    conn = MagicMock()
    cur = MagicMock()
    cur.fetchone.return_value = fetchone_return
    cur.fetchall.return_value = fetchall_return or []

    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=cur)
    ctx.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = ctx

    return conn, cur


def _rule(check_type: str, threshold: dict, column_name: str | None = None) -> AuditRule:
    """Build a minimal AuditRule for testing."""
    return AuditRule(
        rule_id=f"eia.retail_sales.{check_type}",
        source="eia",
        dataset="retail_sales",
        check_type=check_type,
        column_name=column_name,
        threshold=threshold,
    )


RUN_ID = "test-run-001"


# ---------------------------------------------------------------------------
# check_null_rate
# ---------------------------------------------------------------------------


class TestCheckNullRate:
    def test_pass_when_null_rate_below_threshold(self):
        """3% nulls against a 5% threshold should pass."""
        conn, _ = _mock_conn(fetchone_return={"total": 1000, "nulls": 30})
        rule = _rule("null_rate", {"max_null_pct": 5.0}, column_name="sales")
        result = check_null_rate(conn, rule, RUN_ID)
        assert result.status == "pass"
        assert result.is_pass
        assert result.measured_value["null_pct"] == pytest.approx(3.0, rel=1e-3)

    def test_fail_when_null_rate_exceeds_threshold(self):
        """12% nulls against a 5% threshold should fail."""
        conn, _ = _mock_conn(fetchone_return={"total": 1000, "nulls": 120})
        rule = _rule("null_rate", {"max_null_pct": 5.0}, column_name="sales")
        result = check_null_rate(conn, rule, RUN_ID)
        assert result.status == "fail"
        assert not result.is_pass
        assert result.measured_value["null_pct"] == pytest.approx(12.0, rel=1e-3)
        assert "12.0%" in result.detail or "12%" in result.detail

    def test_warn_when_table_is_empty(self):
        """Zero rows can't produce a meaningful rate — return warn."""
        conn, _ = _mock_conn(fetchone_return={"total": 0, "nulls": 0})
        rule = _rule("null_rate", {"max_null_pct": 5.0}, column_name="sales")
        result = check_null_rate(conn, rule, RUN_ID)
        assert result.status == "warn"
        assert result.measured_value["null_pct"] is None

    def test_pass_at_exact_threshold(self):
        """Null rate equal to threshold should pass (boundary is inclusive)."""
        conn, _ = _mock_conn(fetchone_return={"total": 100, "nulls": 5})
        rule = _rule("null_rate", {"max_null_pct": 5.0}, column_name="revenue")
        result = check_null_rate(conn, rule, RUN_ID)
        assert result.status == "pass"

    def test_measured_value_contains_expected_keys(self):
        conn, _ = _mock_conn(fetchone_return={"total": 500, "nulls": 10})
        rule = _rule("null_rate", {"max_null_pct": 10.0}, column_name="price")
        result = check_null_rate(conn, rule, RUN_ID)
        assert set(result.measured_value.keys()) >= {"total", "nulls", "null_pct"}


# ---------------------------------------------------------------------------
# check_staleness
# ---------------------------------------------------------------------------


class TestCheckStaleness:
    def _recent_period(self, months_ago: int = 1) -> date:
        """Return the first day of the month N months before today."""
        today = date.today()
        month = today.month - months_ago
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        return date(year, month, 1)

    def test_pass_when_data_is_recent(self):
        """Period 1 month ago should pass a 3-month threshold."""
        recent = self._recent_period(months_ago=1)
        conn, _ = _mock_conn(fetchone_return={"max_period": recent})
        rule = _rule("staleness", {"max_months_behind": 3})
        result = check_staleness(conn, rule, RUN_ID)
        assert result.status == "pass"
        assert result.measured_value["months_behind"] == 1

    def test_fail_when_data_is_stale(self):
        """Period 24 months ago should fail a 3-month threshold."""
        old = date(date.today().year - 2, date.today().month, 1)
        conn, _ = _mock_conn(fetchone_return={"max_period": old})
        rule = _rule("staleness", {"max_months_behind": 3})
        result = check_staleness(conn, rule, RUN_ID)
        assert result.status == "fail"
        assert result.measured_value["months_behind"] >= 24

    def test_fail_when_table_has_no_data(self):
        """NULL max_period means no data — must fail."""
        conn, _ = _mock_conn(fetchone_return={"max_period": None})
        rule = _rule("staleness", {"max_months_behind": 3})
        result = check_staleness(conn, rule, RUN_ID)
        assert result.status == "fail"
        assert "no data" in result.detail.lower()

    def test_pass_at_exact_threshold(self):
        """Exactly at threshold should pass."""
        today = date.today()
        max_months = 6
        month = today.month - max_months
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        boundary = date(year, month, 1)
        conn, _ = _mock_conn(fetchone_return={"max_period": boundary})
        rule = _rule("staleness", {"max_months_behind": max_months})
        result = check_staleness(conn, rule, RUN_ID)
        assert result.status == "pass"

    def test_measured_value_contains_expected_keys(self):
        recent = self._recent_period(months_ago=2)
        conn, _ = _mock_conn(fetchone_return={"max_period": recent})
        rule = _rule("staleness", {"max_months_behind": 6})
        result = check_staleness(conn, rule, RUN_ID)
        assert "max_period" in result.measured_value
        assert "months_behind" in result.measured_value


# ---------------------------------------------------------------------------
# check_row_count
# ---------------------------------------------------------------------------


class TestCheckRowCount:
    def test_pass_when_all_periods_in_range(self):
        """All 12 periods with 52 rows each should pass [50, 60]."""
        rows = [{"period": date(2024, m, 1), "cnt": 52} for m in range(1, 13)]
        conn, _ = _mock_conn(fetchall_return=rows)
        rule = _rule("row_count", {"min_per_month": 50, "max_per_month": 60})
        result = check_row_count(conn, rule, RUN_ID)
        assert result.status == "pass"
        assert result.measured_value["violations"] == []

    def test_fail_when_period_has_too_few_rows(self):
        """One period with only 10 rows should fail [50, 60]."""
        rows = [{"period": date(2024, 1, 1), "cnt": 52}] * 11
        rows.append({"period": date(2023, 12, 1), "cnt": 10})
        conn, _ = _mock_conn(fetchall_return=rows)
        rule = _rule("row_count", {"min_per_month": 50, "max_per_month": 60})
        result = check_row_count(conn, rule, RUN_ID)
        assert result.status == "fail"
        assert len(result.measured_value["violations"]) == 1
        assert result.measured_value["violations"][0]["count"] == 10

    def test_fail_when_table_empty(self):
        conn, _ = _mock_conn(fetchall_return=[])
        rule = _rule("row_count", {"min_per_month": 50, "max_per_month": 60})
        result = check_row_count(conn, rule, RUN_ID)
        assert result.status == "fail"
        assert "no data" in result.detail.lower()

    def test_fail_when_period_exceeds_max(self):
        """Period with 100 rows should fail against max_per_month=60."""
        rows = [{"period": date(2024, 1, 1), "cnt": 100}]
        conn, _ = _mock_conn(fetchall_return=rows)
        rule = _rule("row_count", {"min_per_month": 50, "max_per_month": 60})
        result = check_row_count(conn, rule, RUN_ID)
        assert result.status == "fail"

    def test_pass_counts_periods_checked(self):
        rows = [{"period": date(2024, m, 1), "cnt": 55} for m in range(1, 7)]
        conn, _ = _mock_conn(fetchall_return=rows)
        rule = _rule("row_count", {"min_per_month": 50, "max_per_month": 60})
        result = check_row_count(conn, rule, RUN_ID)
        assert result.measured_value["periods_checked"] == 6


# ---------------------------------------------------------------------------
# check_range
# ---------------------------------------------------------------------------


class TestCheckRange:
    def test_pass_when_values_within_bounds(self):
        """min=0, max=100 within [-10, 200] should pass."""
        conn, _ = _mock_conn(fetchone_return={"min_val": 0.0, "max_val": 100.0})
        rule = _rule("range", {"min": -10.0, "max": 200.0}, column_name="price")
        result = check_range(conn, rule, RUN_ID)
        assert result.status == "pass"

    def test_fail_when_actual_min_below_threshold(self):
        """Actual min -5 below threshold min 0 should fail."""
        conn, _ = _mock_conn(fetchone_return={"min_val": -5.0, "max_val": 100.0})
        rule = _rule("range", {"min": 0.0, "max": 200.0}, column_name="price")
        result = check_range(conn, rule, RUN_ID)
        assert result.status == "fail"
        assert "-5.0" in result.detail or "-5" in result.detail

    def test_fail_when_actual_max_above_threshold(self):
        """Actual max 300 above threshold max 200 should fail."""
        conn, _ = _mock_conn(fetchone_return={"min_val": 10.0, "max_val": 300.0})
        rule = _rule("range", {"min": 0.0, "max": 200.0}, column_name="price")
        result = check_range(conn, rule, RUN_ID)
        assert result.status == "fail"
        assert "300" in result.detail

    def test_fail_when_table_empty(self):
        conn, _ = _mock_conn(fetchone_return={"min_val": None, "max_val": None})
        rule = _rule("range", {"min": 0.0, "max": 200.0}, column_name="price")
        result = check_range(conn, rule, RUN_ID)
        assert result.status == "fail"
        assert "empty" in result.detail.lower()

    def test_measured_value_contains_threshold_bounds(self):
        conn, _ = _mock_conn(fetchone_return={"min_val": 5.0, "max_val": 150.0})
        rule = _rule("range", {"min": 0.0, "max": 200.0}, column_name="price")
        result = check_range(conn, rule, RUN_ID)
        assert result.measured_value["threshold_min"] == 0.0
        assert result.measured_value["threshold_max"] == 200.0


# ---------------------------------------------------------------------------
# check_completeness
# ---------------------------------------------------------------------------


class TestCheckCompleteness:
    def test_pass_when_no_gaps(self):
        """gap_count = 0 should pass."""
        conn, _ = _mock_conn(fetchone_return={"gap_count": 0})
        rule = _rule(
            "completeness",
            {"dimensions": ["stateid"], "frequency": "monthly"},
        )
        result = check_completeness(conn, rule, RUN_ID)
        assert result.status == "pass"
        assert result.measured_value["gap_count"] == 0

    def test_fail_when_gaps_exist(self):
        """gap_count = 42 should fail."""
        conn, _ = _mock_conn(fetchone_return={"gap_count": 42})
        rule = _rule(
            "completeness",
            {"dimensions": ["stateid"], "frequency": "monthly"},
        )
        result = check_completeness(conn, rule, RUN_ID)
        assert result.status == "fail"
        assert result.measured_value["gap_count"] == 42
        assert "42" in result.detail

    def test_fail_detail_mentions_dimensions(self):
        conn, _ = _mock_conn(fetchone_return={"gap_count": 5})
        rule = _rule(
            "completeness",
            {"dimensions": ["stateid", "sectorid"], "frequency": "monthly"},
        )
        result = check_completeness(conn, rule, RUN_ID)
        assert result.status == "fail"
        assert "stateid" in result.detail or "sectorid" in result.detail

    def test_measured_value_contains_dimensions(self):
        conn, _ = _mock_conn(fetchone_return={"gap_count": 0})
        rule = _rule(
            "completeness",
            {"dimensions": ["stateid"], "frequency": "monthly"},
        )
        result = check_completeness(conn, rule, RUN_ID)
        assert result.measured_value["dimensions"] == ["stateid"]


# ---------------------------------------------------------------------------
# run_check dispatcher
# ---------------------------------------------------------------------------


class TestRunCheck:
    def test_dispatches_null_rate(self):
        conn, _ = _mock_conn(fetchone_return={"total": 100, "nulls": 2})
        rule = _rule("null_rate", {"max_null_pct": 5.0}, column_name="sales")
        result = run_check(conn, rule, RUN_ID)
        assert result.rule_id == rule.rule_id
        assert result.status in {"pass", "fail", "warn"}

    def test_dispatches_staleness(self):
        recent = date.today().replace(day=1)
        conn, _ = _mock_conn(fetchone_return={"max_period": recent})
        rule = _rule("staleness", {"max_months_behind": 3})
        result = run_check(conn, rule, RUN_ID)
        assert result.rule_id == rule.rule_id
        assert result.status in {"pass", "fail"}

    def test_dispatches_row_count(self):
        rows = [{"period": date(2024, 1, 1), "cnt": 52}]
        conn, _ = _mock_conn(fetchall_return=rows)
        rule = _rule("row_count", {"min_per_month": 50, "max_per_month": 60})
        result = run_check(conn, rule, RUN_ID)
        assert result.status in {"pass", "fail"}

    def test_dispatches_range(self):
        conn, _ = _mock_conn(fetchone_return={"min_val": 0.0, "max_val": 100.0})
        rule = _rule("range", {"min": -10.0, "max": 200.0}, column_name="price")
        result = run_check(conn, rule, RUN_ID)
        assert result.status in {"pass", "fail"}

    def test_dispatches_completeness(self):
        conn, _ = _mock_conn(fetchone_return={"gap_count": 0})
        rule = _rule("completeness", {"dimensions": ["stateid"], "frequency": "monthly"})
        result = run_check(conn, rule, RUN_ID)
        assert result.status in {"pass", "fail"}

    def test_unknown_check_type_returns_error(self):
        conn, _ = _mock_conn()
        rule = _rule("nonexistent_check", {})
        result = run_check(conn, rule, RUN_ID)
        assert result.status == "error"
        assert "nonexistent_check" in result.detail

    def test_exception_in_check_returns_error(self):
        """If the underlying check raises, run_check wraps it in an error result."""
        conn = MagicMock()
        # Make the cursor context manager raise on execute
        cur = MagicMock()
        cur.execute.side_effect = RuntimeError("DB went away")
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=cur)
        ctx.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = ctx

        rule = _rule("null_rate", {"max_null_pct": 5.0}, column_name="sales")
        result = run_check(conn, rule, RUN_ID)
        assert result.status == "error"
        assert "RuntimeError" in result.detail or "DB went away" in result.detail

    def test_error_result_has_correct_rule_id(self):
        conn, _ = _mock_conn()
        rule = _rule("bogus_type", {})
        result = run_check(conn, rule, RUN_ID)
        assert result.rule_id == rule.rule_id

    def test_error_result_has_correct_run_id(self):
        conn, _ = _mock_conn()
        rule = _rule("bogus_type", {})
        result = run_check(conn, rule, "specific-run-id")
        assert result.run_id == "specific-run-id"
