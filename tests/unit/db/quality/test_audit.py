"""Unit tests for energy_usa.db.quality.audit (no real DB required).

All database calls are intercepted with MagicMock so these tests run quickly
in CI without a Postgres instance.  The goal is to verify:

- Dataclass construction and property behaviour (AuditRule, AuditResult).
- That load_rules, write_result, and upsert_rules build the correct SQL
  parameters and exercise the cursor correctly.
"""

import json
from unittest.mock import MagicMock, call

import pytest

from energy_usa.db.quality.audit import (
    AuditResult,
    AuditRule,
    load_rules,
    upsert_rules,
    write_result,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_conn(fetchall_return=None, fetchone_return=None):
    """Return a (conn, cursor) pair where cursor is a MagicMock.

    The cursor is returned from conn.cursor().__enter__() so it works with the
    ``with conn.cursor() as cur:`` pattern used in the module under test.
    """
    conn = MagicMock()
    cur = MagicMock()
    cur.fetchall.return_value = fetchall_return or []
    cur.fetchone.return_value = fetchone_return

    # Support context-manager protocol: ``with conn.cursor() as cur``
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=cur)
    ctx.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = ctx

    return conn, cur


def _sample_rule_dict(**overrides):
    base = {
        "rule_id": "eia.retail_sales.null_rate",
        "source": "eia",
        "dataset": "retail_sales",
        "check_type": "null_rate",
        "column_name": "sales",
        "threshold": {"max_null_pct": 5.0},
        "enabled": True,
    }
    base.update(overrides)
    return base


def _sample_rule(**overrides) -> AuditRule:
    return AuditRule.from_dict(_sample_rule_dict(**overrides))


# ---------------------------------------------------------------------------
# AuditRule dataclass tests
# ---------------------------------------------------------------------------


class TestAuditRuleFromDict:
    def test_basic_construction(self):
        rule = _sample_rule()
        assert rule.rule_id == "eia.retail_sales.null_rate"
        assert rule.source == "eia"
        assert rule.dataset == "retail_sales"
        assert rule.check_type == "null_rate"
        assert rule.column_name == "sales"
        assert rule.threshold == {"max_null_pct": 5.0}
        assert rule.enabled is True

    def test_threshold_as_json_string(self):
        """from_dict must parse threshold when it arrives as a JSON string."""
        row = _sample_rule_dict(threshold='{"max_null_pct": 10.0}')
        rule = AuditRule.from_dict(row)
        assert rule.threshold == {"max_null_pct": 10.0}

    def test_threshold_as_dict(self):
        """from_dict must accept an already-decoded dict (psycopg3 default)."""
        row = _sample_rule_dict(threshold={"max_null_pct": 3.5})
        rule = AuditRule.from_dict(row)
        assert rule.threshold == {"max_null_pct": 3.5}

    def test_column_name_none(self):
        row = _sample_rule_dict(column_name=None)
        rule = AuditRule.from_dict(row)
        assert rule.column_name is None

    def test_enabled_defaults_to_true_when_missing(self):
        row = _sample_rule_dict()
        del row["enabled"]
        rule = AuditRule.from_dict(row)
        assert rule.enabled is True

    def test_enabled_false(self):
        rule = _sample_rule(enabled=False)
        assert rule.enabled is False


class TestAuditRuleTableName:
    def test_table_name_combines_source_and_dataset(self):
        rule = _sample_rule()
        assert rule.table_name == "eia.retail_sales"

    def test_table_name_reflects_different_source_and_dataset(self):
        rule = _sample_rule(source="transform", dataset="electricity_demand")
        assert rule.table_name == "transform.electricity_demand"


# ---------------------------------------------------------------------------
# AuditResult dataclass tests
# ---------------------------------------------------------------------------


class TestAuditResult:
    def test_is_pass_true_for_pass_status(self):
        result = AuditResult(rule_id="r1", run_id="run1", status="pass")
        assert result.is_pass is True

    def test_is_pass_false_for_fail(self):
        result = AuditResult(rule_id="r1", run_id="run1", status="fail")
        assert result.is_pass is False

    def test_is_pass_false_for_warn(self):
        result = AuditResult(rule_id="r1", run_id="run1", status="warn")
        assert result.is_pass is False

    def test_is_pass_false_for_error(self):
        result = AuditResult(rule_id="r1", run_id="run1", status="error")
        assert result.is_pass is False

    def test_defaults(self):
        result = AuditResult(rule_id="r1", run_id="run1", status="pass")
        assert result.measured_value is None
        assert result.detail is None

    def test_full_construction(self):
        result = AuditResult(
            rule_id="r1",
            run_id="run1",
            status="fail",
            measured_value={"null_pct": 12.0},
            detail="null rate 12% exceeds threshold 5%",
        )
        assert result.measured_value == {"null_pct": 12.0}
        assert "12%" in result.detail


# ---------------------------------------------------------------------------
# load_rules tests
# ---------------------------------------------------------------------------


class TestLoadRules:
    def test_load_rules_with_source_filter(self):
        """Verifies the correct SQL parameter is passed for source filter."""
        db_rows = [
            _sample_rule_dict(),
            _sample_rule_dict(
                rule_id="eia.electric_power_operational.staleness",
                dataset="electric_power_operational",
                check_type="staleness",
                threshold={"max_months_behind": 3},
                column_name=None,
            ),
        ]
        conn, cur = _mock_conn(fetchall_return=db_rows)
        rules = load_rules(conn, source="eia")

        assert len(rules) == 2
        assert all(isinstance(r, AuditRule) for r in rules)

        # Verify SQL was executed with the right params
        execute_call = cur.execute.call_args
        params = execute_call[0][1]
        assert params["source"] == "eia"
        assert "datasets" not in params

    def test_load_rules_with_dataset_filter(self):
        """When datasets is provided, the SQL includes the dataset filter."""
        db_rows = [_sample_rule_dict()]
        conn, cur = _mock_conn(fetchall_return=db_rows)
        rules = load_rules(conn, source="eia", datasets=["retail_sales"])

        assert len(rules) == 1
        params = cur.execute.call_args[0][1]
        assert params["source"] == "eia"
        assert params["datasets"] == ["retail_sales"]

    def test_load_rules_empty_result(self):
        conn, cur = _mock_conn(fetchall_return=[])
        rules = load_rules(conn, source="eia")
        assert rules == []

    def test_load_rules_threshold_json_string_decoded(self):
        """Simulates a cursor that returns threshold as a raw JSON string."""
        db_rows = [_sample_rule_dict(threshold='{"max_null_pct": 7}')]
        conn, cur = _mock_conn(fetchall_return=db_rows)
        rules = load_rules(conn, source="eia")
        assert rules[0].threshold == {"max_null_pct": 7}

    def test_load_rules_multiple_datasets_filter(self):
        conn, cur = _mock_conn(fetchall_return=[])
        load_rules(conn, source="eia", datasets=["retail_sales", "natural_gas_prices"])
        params = cur.execute.call_args[0][1]
        assert params["datasets"] == ["retail_sales", "natural_gas_prices"]


# ---------------------------------------------------------------------------
# write_result tests
# ---------------------------------------------------------------------------


class TestWriteResult:
    def test_write_result_executes_insert(self):
        conn, cur = _mock_conn()
        result = AuditResult(
            rule_id="eia.retail_sales.null_rate",
            run_id="run-abc",
            status="pass",
            measured_value={"total": 1000, "nulls": 30, "null_pct": 3.0},
            detail=None,
        )
        write_result(conn, result)

        cur.execute.assert_called_once()
        params = cur.execute.call_args[0][1]
        assert params["rule_id"] == "eia.retail_sales.null_rate"
        assert params["run_id"] == "run-abc"
        assert params["status"] == "pass"
        assert params["detail"] is None

    def test_write_result_serialises_measured_value_to_json(self):
        """measured_value must be passed as a JSON string, not a raw dict."""
        conn, cur = _mock_conn()
        result = AuditResult(
            rule_id="r1",
            run_id="run1",
            status="fail",
            measured_value={"null_pct": 12.0},
        )
        write_result(conn, result)
        params = cur.execute.call_args[0][1]
        # Should be a JSON string, parseable back to dict
        parsed = json.loads(params["measured_value"])
        assert parsed == {"null_pct": 12.0}

    def test_write_result_null_measured_value_stays_none(self):
        conn, cur = _mock_conn()
        result = AuditResult(rule_id="r1", run_id="run1", status="error")
        write_result(conn, result)
        params = cur.execute.call_args[0][1]
        assert params["measured_value"] is None

    def test_write_result_commits(self):
        conn, _ = _mock_conn()
        result = AuditResult(rule_id="r1", run_id="run1", status="pass")
        write_result(conn, result)
        conn.commit.assert_called_once()


# ---------------------------------------------------------------------------
# upsert_rules tests
# ---------------------------------------------------------------------------


class TestUpsertRules:
    def test_upsert_empty_list_returns_zero(self):
        conn, cur = _mock_conn()
        count = upsert_rules(conn, [])
        assert count == 0
        cur.executemany.assert_not_called()

    def test_upsert_single_rule(self):
        conn, cur = _mock_conn()
        rules = [_sample_rule()]
        count = upsert_rules(conn, rules)
        assert count == 1
        cur.executemany.assert_called_once()

    def test_upsert_multiple_rules_returns_count(self):
        conn, cur = _mock_conn()
        rules = [
            _sample_rule(),
            _sample_rule(
                rule_id="eia.retail_sales.staleness",
                check_type="staleness",
                threshold={"max_months_behind": 3},
                column_name=None,
            ),
        ]
        count = upsert_rules(conn, rules)
        assert count == 2

    def test_upsert_serialises_threshold_to_json(self):
        """Threshold must be JSON-encoded before being sent to psycopg."""
        conn, cur = _mock_conn()
        rules = [_sample_rule(threshold={"max_null_pct": 5.0})]
        upsert_rules(conn, rules)

        params_list = cur.executemany.call_args[0][1]
        threshold_val = params_list[0]["threshold"]
        # Should be a JSON string (so psycopg can cast to JSONB)
        parsed = json.loads(threshold_val)
        assert parsed == {"max_null_pct": 5.0}

    def test_upsert_commits(self):
        conn, _ = _mock_conn()
        upsert_rules(conn, [_sample_rule()])
        conn.commit.assert_called_once()

    def test_upsert_includes_on_conflict_clause_in_sql(self):
        """Sanity-check that the SQL sent to executemany contains ON CONFLICT."""
        conn, cur = _mock_conn()
        upsert_rules(conn, [_sample_rule()])
        sql = cur.executemany.call_args[0][0]
        assert "ON CONFLICT" in sql
        assert "DO UPDATE SET" in sql
