# Validation System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an isolated validation system that checks data quality (null rates, completeness, staleness, row counts, value ranges) by running Prefect flows against ingested data and recording results in the `quality` schema.

**Architecture:** Validation is completely separate from ingestion. A validate spec (`specs/validate/eia.md`) describes quality expectations per dataset. The generator produces `quality.audit_rules` seed SQL. At runtime, a single Prefect flow per source loads rules from the database, runs generic SQL checks, and writes results to `quality.audit_results`. Five check types are implemented as pure SQL queries — no Python business logic, just parameterized SQL patterns.

**Tech Stack:** Python 3.12, psycopg3, Prefect 2, PostgreSQL 16, Jinja2

**Design Spec:** `docs/superpowers/specs/2026-04-10-markdown-driven-data-platform-design.md` — Quality & Validation System section.

**Depends on:** Plan 1 (quality schema DDL exists), Plan 2 (generator infrastructure).

---

## File Map

### Created
```
src/energy_usa/db/quality/__init__.py
src/energy_usa/db/quality/audit.py               # load_rules, write_result, upsert_rules
src/energy_usa/db/quality/checks.py              # 5 check functions (pure SQL)
src/energy_usa/flows/validate/__init__.py
src/energy_usa/flows/validate/eia.py             # Prefect validation flow
src/energy_usa/generators/validate.py            # Generate audit_rules SQL from spec
src/energy_usa/generators/models_validate.py     # ValidationSpec dataclasses
src/energy_usa/generators/parse_validate.py      # Parse validate spec markdown
src/energy_usa/generators/templates/audit_rules.sql.j2
specs/validate/eia.md                            # Quality expectations for EIA datasets
scripts/validate.py                              # CLI for running validation
tests/unit/db/quality/__init__.py
tests/unit/db/quality/test_checks.py
tests/unit/generators/test_parse_validate.py
tests/unit/generators/test_validate_gen.py
```

### Modified
```
src/energy_usa/db/__init__.py                     # Add quality exports
src/energy_usa/flows/__init__.py                  # Add validate export
docker/superset/seed_databases.py                 # Add quality.audit_results dataset
scripts/generate.py                               # Add validate subcommand
Makefile                                          # Add validate, audit, generate-validate targets
CLAUDE.md                                         # Document validation commands
```

---

## Task 1: Quality DB Module — Audit Operations

Database operations for the quality schema: loading rules, writing results, upserting rules.

**Files:**
- Create: `src/energy_usa/db/quality/__init__.py`
- Create: `src/energy_usa/db/quality/audit.py`
- Test: `tests/unit/db/quality/test_audit.py`

- [ ] **Step 1: Write tests for audit operations**

```python
# tests/unit/db/quality/test_audit.py
"""Tests for quality audit database operations."""
from datetime import date, datetime
from unittest.mock import MagicMock

from energy_usa.db.quality.audit import (
    AuditRule,
    AuditResult,
    load_rules,
    write_result,
    upsert_rules,
)


def _mock_conn(rows=None):
    """Return a mock connection that returns given rows from fetchall."""
    conn = MagicMock()
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchall.return_value = rows or []
    conn.cursor.return_value = cursor
    return conn, cursor


def test_audit_rule_from_dict():
    row = {
        "rule_id": "eia.retail_sales.null_rate.revenue",
        "source": "eia",
        "dataset": "retail_sales",
        "check_type": "null_rate",
        "column_name": "revenue",
        "threshold": {"max_null_pct": 5},
        "enabled": True,
    }
    rule = AuditRule.from_dict(row)
    assert rule.rule_id == "eia.retail_sales.null_rate.revenue"
    assert rule.check_type == "null_rate"
    assert rule.threshold == {"max_null_pct": 5}
    assert rule.table_name == "eia.retail_sales"


def test_audit_result_pass():
    result = AuditResult(
        rule_id="test.rule",
        run_id="run-123",
        status="pass",
        measured_value={"null_pct": 2.1},
        detail=None,
    )
    assert result.status == "pass"
    assert result.is_pass


def test_audit_result_fail():
    result = AuditResult(
        rule_id="test.rule",
        run_id="run-123",
        status="fail",
        measured_value={"null_pct": 12.0},
        detail="revenue null rate 12.0% exceeds threshold 5%",
    )
    assert not result.is_pass


def test_load_rules_filters_by_source():
    rows = [
        {"rule_id": "eia.r.null_rate.x", "source": "eia", "dataset": "r",
         "check_type": "null_rate", "column_name": "x", "threshold": {}, "enabled": True},
    ]
    conn, cursor = _mock_conn(rows)
    rules = load_rules(conn, source="eia")
    cursor.execute.assert_called_once()
    sql = cursor.execute.call_args[0][0]
    assert "source = %(source)s" in sql
    assert "enabled = true" in sql


def test_load_rules_filters_by_dataset():
    conn, cursor = _mock_conn([])
    load_rules(conn, source="eia", datasets=["retail_sales"])
    sql = cursor.execute.call_args[0][0]
    assert "dataset = ANY(%(datasets)s)" in sql


def test_write_result_inserts():
    conn, cursor = _mock_conn()
    result = AuditResult(
        rule_id="eia.r.null_rate.x",
        run_id="run-1",
        status="pass",
        measured_value={"null_pct": 1.0},
        detail=None,
    )
    write_result(conn, result)
    cursor.execute.assert_called_once()
    sql = cursor.execute.call_args[0][0]
    assert "INSERT INTO quality.audit_results" in sql


def test_upsert_rules_inserts():
    conn, cursor = _mock_conn()
    rules = [
        AuditRule(
            rule_id="eia.r.null_rate.x",
            source="eia", dataset="r",
            check_type="null_rate", column_name="x",
            threshold={"max_null_pct": 5}, enabled=True,
        )
    ]
    upsert_rules(conn, rules)
    cursor.executemany.assert_called_once()
    sql = cursor.executemany.call_args[0][0]
    assert "ON CONFLICT (rule_id) DO UPDATE" in sql
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/db/quality/test_audit.py -v
```

Expected: ModuleNotFoundError

- [ ] **Step 3: Implement audit module**

```python
# src/energy_usa/db/quality/__init__.py
"""Quality audit database operations."""
```

```python
# src/energy_usa/db/quality/audit.py
"""Database operations for the quality.audit_rules and quality.audit_results tables."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import psycopg


@dataclass
class AuditRule:
    """A validation rule loaded from quality.audit_rules."""

    rule_id: str
    source: str
    dataset: str
    check_type: str
    column_name: str | None
    threshold: dict[str, Any]
    enabled: bool

    @property
    def table_name(self) -> str:
        """Fully qualified table name: source.dataset."""
        return f"{self.source}.{self.dataset}"

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> AuditRule:
        """Create from a database row dict."""
        threshold = row["threshold"]
        if isinstance(threshold, str):
            threshold = json.loads(threshold)
        return cls(
            rule_id=row["rule_id"],
            source=row["source"],
            dataset=row["dataset"],
            check_type=row["check_type"],
            column_name=row.get("column_name"),
            threshold=threshold,
            enabled=row.get("enabled", True),
        )


@dataclass
class AuditResult:
    """Result of running a single validation check."""

    rule_id: str
    run_id: str
    status: str  # "pass", "fail", "warn", "error"
    measured_value: dict[str, Any] | None
    detail: str | None

    @property
    def is_pass(self) -> bool:
        return self.status == "pass"


def load_rules(
    conn: psycopg.Connection,
    *,
    source: str,
    datasets: list[str] | None = None,
) -> list[AuditRule]:
    """Load enabled audit rules for a source, optionally filtered by datasets.

    :param conn: Open psycopg connection to the ingest database.
    :param source: Source name (e.g. 'eia').
    :param datasets: Optional list of dataset names to filter by.
    :returns: List of AuditRule objects.
    """
    if datasets:
        sql = """
        SELECT rule_id, source, dataset, check_type, column_name, threshold, enabled
        FROM quality.audit_rules
        WHERE source = %(source)s AND dataset = ANY(%(datasets)s) AND enabled = true
        ORDER BY dataset, check_type, column_name
        """
        params = {"source": source, "datasets": datasets}
    else:
        sql = """
        SELECT rule_id, source, dataset, check_type, column_name, threshold, enabled
        FROM quality.audit_rules
        WHERE source = %(source)s AND enabled = true
        ORDER BY dataset, check_type, column_name
        """
        params = {"source": source}
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return [AuditRule.from_dict(r) for r in rows]


def write_result(conn: psycopg.Connection, result: AuditResult) -> None:
    """Write a single audit result to quality.audit_results.

    :param conn: Open psycopg connection.
    :param result: The check result to persist.
    """
    sql = """
    INSERT INTO quality.audit_results (rule_id, run_id, status, measured_value, detail)
    VALUES (%(rule_id)s, %(run_id)s, %(status)s, %(measured_value)s, %(detail)s)
    """
    with conn.cursor() as cur:
        cur.execute(sql, {
            "rule_id": result.rule_id,
            "run_id": result.run_id,
            "status": result.status,
            "measured_value": json.dumps(result.measured_value) if result.measured_value else None,
            "detail": result.detail,
        })
    conn.commit()


def upsert_rules(conn: psycopg.Connection, rules: list[AuditRule]) -> int:
    """Insert or update audit rules. Returns count of rules upserted.

    :param conn: Open psycopg connection.
    :param rules: List of AuditRule objects to persist.
    :returns: Number of rules upserted.
    """
    if not rules:
        return 0
    sql = """
    INSERT INTO quality.audit_rules
        (rule_id, source, dataset, check_type, column_name, threshold, enabled)
    VALUES
        (%(rule_id)s, %(source)s, %(dataset)s, %(check_type)s, %(column_name)s, %(threshold)s, %(enabled)s)
    ON CONFLICT (rule_id) DO UPDATE SET
        check_type = EXCLUDED.check_type,
        column_name = EXCLUDED.column_name,
        threshold = EXCLUDED.threshold,
        enabled = EXCLUDED.enabled
    """
    params = [
        {
            "rule_id": r.rule_id,
            "source": r.source,
            "dataset": r.dataset,
            "check_type": r.check_type,
            "column_name": r.column_name,
            "threshold": json.dumps(r.threshold),
            "enabled": r.enabled,
        }
        for r in rules
    ]
    with conn.cursor() as cur:
        cur.executemany(sql, params)
    conn.commit()
    return len(rules)
```

- [ ] **Step 4: Create test __init__.py and run tests**

```bash
mkdir -p tests/unit/db/quality
touch tests/unit/db/quality/__init__.py
uv run pytest tests/unit/db/quality/ -v
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add src/energy_usa/db/quality/ tests/unit/db/quality/
git commit -m "add quality audit db module (load_rules, write_result, upsert_rules)

AuditRule and AuditResult dataclasses plus database operations for the
quality.audit_rules and quality.audit_results tables. Rules are loaded
by source with optional dataset filter. Results are written per-check."
```

---

## Task 2: Validation Check Functions

Five generic SQL check functions that each take a connection and a rule, execute a query, and return an AuditResult.

**Files:**
- Create: `src/energy_usa/db/quality/checks.py`
- Test: `tests/unit/db/quality/test_checks.py`

- [ ] **Step 1: Write tests for check functions**

```python
# tests/unit/db/quality/test_checks.py
"""Tests for validation check SQL functions.

These test the SQL generation and result interpretation, not actual DB queries.
We mock the cursor to return specific row results.
"""
from unittest.mock import MagicMock

from energy_usa.db.quality.audit import AuditRule
from energy_usa.db.quality.checks import (
    check_null_rate,
    check_staleness,
    check_row_count,
    check_range,
    check_completeness,
    run_check,
)


def _mock_conn(fetchone_result=None, fetchall_result=None):
    conn = MagicMock()
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = fetchone_result
    cursor.fetchall.return_value = fetchall_result or []
    conn.cursor.return_value = cursor
    return conn, cursor


def _rule(check_type, threshold, column_name=None, dataset="retail_sales"):
    return AuditRule(
        rule_id=f"eia.{dataset}.{check_type}.{column_name or 'all'}",
        source="eia", dataset=dataset,
        check_type=check_type, column_name=column_name,
        threshold=threshold, enabled=True,
    )


# --- null_rate ---

def test_null_rate_pass():
    conn, cur = _mock_conn(fetchone_result={"total": 1000, "nulls": 30})
    result = check_null_rate(conn, _rule("null_rate", {"max_null_pct": 5}, "revenue"), "run-1")
    assert result.status == "pass"
    assert result.measured_value["null_pct"] == 3.0


def test_null_rate_fail():
    conn, cur = _mock_conn(fetchone_result={"total": 100, "nulls": 12})
    result = check_null_rate(conn, _rule("null_rate", {"max_null_pct": 5}, "revenue"), "run-1")
    assert result.status == "fail"
    assert result.measured_value["null_pct"] == 12.0


def test_null_rate_zero_rows():
    conn, cur = _mock_conn(fetchone_result={"total": 0, "nulls": 0})
    result = check_null_rate(conn, _rule("null_rate", {"max_null_pct": 5}, "revenue"), "run-1")
    assert result.status == "warn"


# --- staleness ---

def test_staleness_pass():
    from datetime import date, timedelta
    recent = date.today() - timedelta(days=30)
    conn, cur = _mock_conn(fetchone_result={"max_period": recent})
    result = check_staleness(conn, _rule("staleness", {"max_months_behind": 3}), "run-1")
    assert result.status == "pass"


def test_staleness_fail():
    from datetime import date, timedelta
    old = date.today() - timedelta(days=200)
    conn, cur = _mock_conn(fetchone_result={"max_period": old})
    result = check_staleness(conn, _rule("staleness", {"max_months_behind": 3}), "run-1")
    assert result.status == "fail"


def test_staleness_no_data():
    conn, cur = _mock_conn(fetchone_result={"max_period": None})
    result = check_staleness(conn, _rule("staleness", {"max_months_behind": 3}), "run-1")
    assert result.status == "fail"


# --- row_count ---

def test_row_count_pass():
    conn, cur = _mock_conn(fetchall_result=[
        {"period": "2024-01-01", "cnt": 50},
        {"period": "2024-02-01", "cnt": 48},
    ])
    result = check_row_count(conn, _rule("row_count", {"min_per_month": 40, "max_per_month": 60}), "run-1")
    assert result.status == "pass"


def test_row_count_fail_too_few():
    conn, cur = _mock_conn(fetchall_result=[
        {"period": "2024-01-01", "cnt": 10},
    ])
    result = check_row_count(conn, _rule("row_count", {"min_per_month": 40, "max_per_month": 60}), "run-1")
    assert result.status == "fail"


# --- range ---

def test_range_pass():
    conn, cur = _mock_conn(fetchone_result={"min_val": 0.05, "max_val": 45.0})
    result = check_range(conn, _rule("range", {"column": "price", "min": 0, "max": 100}, "price"), "run-1")
    assert result.status == "pass"


def test_range_fail():
    conn, cur = _mock_conn(fetchone_result={"min_val": -5.0, "max_val": 45.0})
    result = check_range(conn, _rule("range", {"column": "price", "min": 0, "max": 100}, "price"), "run-1")
    assert result.status == "fail"


# --- completeness ---

def test_completeness_pass():
    conn, cur = _mock_conn(fetchone_result={"gap_count": 0})
    result = check_completeness(
        conn, _rule("completeness", {"dimensions": ["stateid"], "frequency": "monthly"}), "run-1"
    )
    assert result.status == "pass"


def test_completeness_fail():
    conn, cur = _mock_conn(fetchone_result={"gap_count": 42})
    result = check_completeness(
        conn, _rule("completeness", {"dimensions": ["stateid"], "frequency": "monthly"}), "run-1"
    )
    assert result.status == "fail"
    assert result.measured_value["gap_count"] == 42


# --- dispatch ---

def test_run_check_dispatches_null_rate():
    conn, cur = _mock_conn(fetchone_result={"total": 100, "nulls": 1})
    result = run_check(conn, _rule("null_rate", {"max_null_pct": 5}, "revenue"), "run-1")
    assert result.status == "pass"


def test_run_check_unknown_type():
    conn, _ = _mock_conn()
    result = run_check(conn, _rule("unknown_type", {}), "run-1")
    assert result.status == "error"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/db/quality/test_checks.py -v
```

Expected: ImportError

- [ ] **Step 3: Implement check functions**

```python
# src/energy_usa/db/quality/checks.py
"""Generic validation check functions.

Each function takes a connection, an AuditRule, and a run_id. It executes
a SQL query against the rule's target table and returns an AuditResult.
Table and column names are constructed from the rule — they are NOT user
input and come from the controlled audit_rules table.
"""

from __future__ import annotations

from datetime import date

import psycopg

from energy_usa.db.quality.audit import AuditResult, AuditRule


def run_check(conn: psycopg.Connection, rule: AuditRule, run_id: str) -> AuditResult:
    """Dispatch to the appropriate check function based on rule.check_type.

    :param conn: Open psycopg connection.
    :param rule: The audit rule to execute.
    :param run_id: Prefect flow run ID or unique identifier for this validation run.
    :returns: AuditResult with pass/fail/warn/error status.
    """
    dispatch = {
        "null_rate": check_null_rate,
        "staleness": check_staleness,
        "row_count": check_row_count,
        "range": check_range,
        "completeness": check_completeness,
    }
    fn = dispatch.get(rule.check_type)
    if fn is None:
        return AuditResult(
            rule_id=rule.rule_id,
            run_id=run_id,
            status="error",
            measured_value=None,
            detail=f"Unknown check type: {rule.check_type}",
        )
    try:
        return fn(conn, rule, run_id)
    except Exception as exc:
        return AuditResult(
            rule_id=rule.rule_id,
            run_id=run_id,
            status="error",
            measured_value=None,
            detail=f"Check raised {type(exc).__name__}: {exc}",
        )


def check_null_rate(conn: psycopg.Connection, rule: AuditRule, run_id: str) -> AuditResult:
    """Check percentage of NULL values in a column.

    Threshold: {"max_null_pct": N}
    """
    table = rule.table_name
    col = rule.column_name
    max_pct = rule.threshold.get("max_null_pct", 0)

    # Table and column names come from audit_rules (controlled data, not user input).
    sql = f"""
    SELECT count(*) AS total,
           count(*) FILTER (WHERE {col} IS NULL) AS nulls
    FROM {table}
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()

    total = row["total"]
    nulls = row["nulls"]
    if total == 0:
        return AuditResult(
            rule_id=rule.rule_id, run_id=run_id, status="warn",
            measured_value={"total": 0, "nulls": 0, "null_pct": 0},
            detail=f"No rows in {table}",
        )

    null_pct = round(nulls * 100.0 / total, 1)
    status = "pass" if null_pct <= max_pct else "fail"
    detail = None if status == "pass" else f"{col} null rate {null_pct}% exceeds threshold {max_pct}%"

    return AuditResult(
        rule_id=rule.rule_id, run_id=run_id, status=status,
        measured_value={"total": total, "nulls": nulls, "null_pct": null_pct},
        detail=detail,
    )


def check_staleness(conn: psycopg.Connection, rule: AuditRule, run_id: str) -> AuditResult:
    """Check that the most recent period is within N months of today.

    Threshold: {"max_months_behind": N}
    """
    table = rule.table_name
    max_months = rule.threshold.get("max_months_behind", 3)

    sql = f"SELECT max(period) AS max_period FROM {table}"
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()

    max_period = row["max_period"]
    if max_period is None:
        return AuditResult(
            rule_id=rule.rule_id, run_id=run_id, status="fail",
            measured_value={"max_period": None},
            detail=f"No data in {table}",
        )

    today = date.today()
    months_behind = (today.year - max_period.year) * 12 + (today.month - max_period.month)
    status = "pass" if months_behind <= max_months else "fail"
    detail = None if status == "pass" else f"Most recent period {max_period} is {months_behind} months behind (threshold: {max_months})"

    return AuditResult(
        rule_id=rule.rule_id, run_id=run_id, status=status,
        measured_value={"max_period": str(max_period), "months_behind": months_behind},
        detail=detail,
    )


def check_row_count(conn: psycopg.Connection, rule: AuditRule, run_id: str) -> AuditResult:
    """Check that row counts per period fall within expected range.

    Threshold: {"min_per_month": N, "max_per_month": N}
    """
    table = rule.table_name
    min_count = rule.threshold.get("min_per_month", 0)
    max_count = rule.threshold.get("max_per_month", float("inf"))

    sql = f"""
    SELECT period, count(*) AS cnt
    FROM {table}
    GROUP BY period
    ORDER BY period DESC
    LIMIT 12
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

    if not rows:
        return AuditResult(
            rule_id=rule.rule_id, run_id=run_id, status="warn",
            measured_value={"periods_checked": 0},
            detail=f"No data in {table}",
        )

    violations = []
    for row in rows:
        cnt = row["cnt"]
        if cnt < min_count or cnt > max_count:
            violations.append({"period": str(row["period"]), "count": cnt})

    status = "pass" if not violations else "fail"
    detail = None if status == "pass" else f"{len(violations)} periods outside range [{min_count}, {max_count}]"

    return AuditResult(
        rule_id=rule.rule_id, run_id=run_id, status=status,
        measured_value={"periods_checked": len(rows), "violations": violations[:5]},
        detail=detail,
    )


def check_range(conn: psycopg.Connection, rule: AuditRule, run_id: str) -> AuditResult:
    """Check that numeric values fall within plausible bounds.

    Threshold: {"column": "col", "min": N, "max": N}
    """
    table = rule.table_name
    col = rule.threshold.get("column", rule.column_name)
    range_min = rule.threshold.get("min")
    range_max = rule.threshold.get("max")

    sql = f"SELECT min({col}) AS min_val, max({col}) AS max_val FROM {table}"
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()

    min_val = row["min_val"]
    max_val = row["max_val"]

    if min_val is None or max_val is None:
        return AuditResult(
            rule_id=rule.rule_id, run_id=run_id, status="warn",
            measured_value={"min_val": None, "max_val": None},
            detail=f"No non-null values in {table}.{col}",
        )

    violations = []
    if range_min is not None and min_val < range_min:
        violations.append(f"min {min_val} < {range_min}")
    if range_max is not None and max_val > range_max:
        violations.append(f"max {max_val} > {range_max}")

    status = "pass" if not violations else "fail"
    detail = None if status == "pass" else f"{col}: {', '.join(violations)}"

    return AuditResult(
        rule_id=rule.rule_id, run_id=run_id, status=status,
        measured_value={"min_val": float(min_val), "max_val": float(max_val)},
        detail=detail,
    )


def check_completeness(conn: psycopg.Connection, rule: AuditRule, run_id: str) -> AuditResult:
    """Check that every expected dimension combo has data for every period.

    Threshold: {"dimensions": ["stateid"], "frequency": "monthly"}
    Uses a cross-join of distinct dimensions x distinct periods, then LEFT
    JOINs actual data to find gaps.
    """
    table = rule.table_name
    dims = rule.threshold.get("dimensions", [])

    if not dims:
        return AuditResult(
            rule_id=rule.rule_id, run_id=run_id, status="error",
            measured_value=None,
            detail="Completeness check requires 'dimensions' in threshold",
        )

    dim_cols = ", ".join(dims)
    # Count rows where actual data is missing for a dimension+period combo
    sql = f"""
    WITH expected AS (
        SELECT DISTINCT {dim_cols}, period
        FROM (SELECT DISTINCT {dim_cols} FROM {table}) d
        CROSS JOIN (SELECT DISTINCT period FROM {table}) p
    ),
    actual AS (
        SELECT DISTINCT {dim_cols}, period FROM {table}
    )
    SELECT count(*) AS gap_count
    FROM expected e
    LEFT JOIN actual a USING ({dim_cols}, period)
    WHERE a.period IS NULL
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()

    gap_count = row["gap_count"]
    status = "pass" if gap_count == 0 else "fail"
    detail = None if status == "pass" else f"{gap_count} missing dimension+period combinations"

    return AuditResult(
        rule_id=rule.rule_id, run_id=run_id, status=status,
        measured_value={"gap_count": gap_count},
        detail=detail,
    )
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/unit/db/quality/ -v
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add src/energy_usa/db/quality/checks.py tests/unit/db/quality/test_checks.py
git commit -m "add five validation check functions (null_rate, staleness, row_count, range, completeness)

Generic SQL check implementations that take a connection and an AuditRule,
execute parameterized SQL against the rule's target table, and return an
AuditResult with pass/fail/warn/error status. run_check() dispatches by type."
```

---

## Task 3: Validation Prefect Flow

A single Prefect flow per source that loads rules, runs checks, and writes results.

**Files:**
- Create: `src/energy_usa/flows/validate/__init__.py`
- Create: `src/energy_usa/flows/validate/eia.py`

- [ ] **Step 1: Create the validation flow**

```python
# src/energy_usa/flows/validate/__init__.py
"""Validation flows, organized by source."""
```

```python
# src/energy_usa/flows/validate/eia.py
"""Prefect flow: validate EIA datasets against quality.audit_rules.

Loads enabled rules from the quality schema, runs each check, and writes
results to quality.audit_results. Completely isolated from ingest — reads
from ingest tables but never writes to them.
"""

from prefect import flow, task
from prefect.logging import get_run_logger

from energy_usa.config import Settings
from energy_usa.db.connection import get_connection
from energy_usa.db.quality.audit import AuditResult, load_rules, write_result
from energy_usa.db.quality.checks import run_check


@task(name="run-validation-checks")
def run_validation_checks(
    database_url: str,
    source: str,
    datasets: list[str] | None,
    run_id: str,
) -> list[AuditResult]:
    """Load rules and run all checks, returning results.

    :param database_url: Ingest database URL.
    :param source: Source name (e.g. 'eia').
    :param datasets: Optional dataset filter.
    :param run_id: Unique run identifier.
    :returns: List of check results.
    """
    logger = get_run_logger()
    conn = get_connection(database_url)
    try:
        rules = load_rules(conn, source=source, datasets=datasets)
        logger.info("Loaded %d rules for source=%s", len(rules), source)

        results: list[AuditResult] = []
        for rule in rules:
            result = run_check(conn, rule, run_id)
            write_result(conn, result)
            results.append(result)
            logger.info(
                "  [%s] %s.%s %s %s",
                result.status.upper(),
                rule.dataset,
                rule.column_name or "*",
                rule.check_type,
                result.detail or "",
            )
        return results
    finally:
        conn.close()


@flow(
    name="validate-eia",
    timeout_seconds=3600,
)
def validate_eia(
    datasets: list[str] | None = None,
) -> dict:
    """Validate EIA datasets against quality rules.

    :param datasets: Optional list of dataset names. None = validate all.
    :returns: Summary dict with pass/fail/warn/error counts.
    """
    logger = get_run_logger()
    settings = Settings()
    if not settings.ingest_database_url:
        raise ValueError("INGEST_DATABASE_URL required for validation")

    from prefect.context import get_run_context
    ctx = get_run_context()
    run_id = str(ctx.flow_run.id) if ctx and ctx.flow_run else "manual"

    results = run_validation_checks(
        database_url=settings.ingest_database_url,
        source="eia",
        datasets=datasets,
        run_id=run_id,
    )

    summary = {"pass": 0, "fail": 0, "warn": 0, "error": 0}
    for r in results:
        summary[r.status] = summary.get(r.status, 0) + 1

    logger.info(
        "Validation complete: %d checks — %d pass, %d fail, %d warn, %d error",
        len(results), summary["pass"], summary["fail"], summary["warn"], summary["error"],
    )
    return summary
```

- [ ] **Step 2: Update flows/__init__.py**

Add to `src/energy_usa/flows/__init__.py`:

```python
from energy_usa.flows.validate.eia import validate_eia
```

And add `"validate_eia"` to the `__all__` list.

- [ ] **Step 3: Verify import works**

```bash
uv run python -c "from energy_usa.flows.validate.eia import validate_eia; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/energy_usa/flows/validate/ src/energy_usa/flows/__init__.py
git commit -m "add EIA validation Prefect flow

validate_eia() loads enabled rules from quality.audit_rules, runs each
check against the ingest tables, and writes results to audit_results.
Isolated from ingest — reads only. Summary returned with pass/fail counts."
```

---

## Task 4: Validate Spec Parser and Generator

Parse validate spec markdown into rules and generate audit_rules INSERT SQL.

**Files:**
- Create: `src/energy_usa/generators/models_validate.py`
- Create: `src/energy_usa/generators/parse_validate.py`
- Create: `src/energy_usa/generators/validate.py`
- Create: `src/energy_usa/generators/templates/audit_rules.sql.j2`
- Test: `tests/unit/generators/test_parse_validate.py`
- Test: `tests/unit/generators/test_validate_gen.py`

- [ ] **Step 1: Write validate spec models**

```python
# src/energy_usa/generators/models_validate.py
"""Dataclasses for parsed validation specs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NullToleranceSpec:
    """Null rate threshold for a single column."""
    column: str
    max_null_pct: float


@dataclass
class DatasetValidationSpec:
    """Validation expectations for one dataset."""
    name: str
    date_range_start: str
    null_tolerances: list[NullToleranceSpec] = field(default_factory=list)
    expected_row_count: str = ""
    completeness_dimensions: list[str] = field(default_factory=list)
    completeness_frequency: str = "monthly"
    staleness_months: int = 3
    range_checks: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ValidateSpec:
    """Parsed validate spec for a source."""
    source: str
    datasets: list[DatasetValidationSpec]

    def get_dataset(self, name: str) -> DatasetValidationSpec | None:
        for ds in self.datasets:
            if ds.name == name:
                return ds
        return None
```

- [ ] **Step 2: Write validate spec parser with tests**

```python
# tests/unit/generators/test_parse_validate.py
"""Tests for the validate spec parser."""
import textwrap

from energy_usa.generators.parse_validate import parse_validate_spec


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


def test_parse_source_name():
    spec = parse_validate_spec(SPEC)
    assert spec.source == "eia"


def test_parse_dataset_count():
    spec = parse_validate_spec(SPEC)
    assert len(spec.datasets) == 2


def test_parse_null_tolerances():
    spec = parse_validate_spec(SPEC)
    rs = spec.get_dataset("retail_sales")
    assert len(rs.null_tolerances) == 4
    assert rs.null_tolerances[0].column == "revenue"
    assert rs.null_tolerances[0].max_null_pct == 5.0


def test_parse_staleness():
    spec = parse_validate_spec(SPEC)
    rs = spec.get_dataset("retail_sales")
    assert rs.staleness_months == 3
    co2 = spec.get_dataset("co2_emissions")
    assert co2.staleness_months == 12


def test_parse_completeness():
    spec = parse_validate_spec(SPEC)
    rs = spec.get_dataset("retail_sales")
    assert rs.completeness_dimensions == ["stateid"]
    assert rs.completeness_frequency == "monthly"


def test_parse_date_range():
    spec = parse_validate_spec(SPEC)
    rs = spec.get_dataset("retail_sales")
    assert rs.date_range_start == "2001-01"


def test_co2_no_completeness():
    spec = parse_validate_spec(SPEC)
    co2 = spec.get_dataset("co2_emissions")
    assert co2.completeness_dimensions == []
```

- [ ] **Step 3: Implement the parser**

```python
# src/energy_usa/generators/parse_validate.py
"""Parse validation spec markdown into ValidateSpec dataclasses."""

from __future__ import annotations

import re
from pathlib import Path

from energy_usa.generators.models_validate import (
    DatasetValidationSpec,
    NullToleranceSpec,
    ValidateSpec,
)


def parse_validate_spec(text: str) -> ValidateSpec:
    """Parse a validate spec markdown string."""
    lines = text.splitlines()
    source = _parse_source_name(lines)
    datasets = _parse_datasets(lines)
    return ValidateSpec(source=source, datasets=datasets)


def parse_validate_spec_file(path: Path) -> ValidateSpec:
    """Parse a validate spec from a file path."""
    return parse_validate_spec(path.read_text())


def _parse_source_name(lines: list[str]) -> str:
    for line in lines:
        if line.startswith("# "):
            # "# EIA Validation Rules" → "eia"
            name = line[2:].strip().split()[0].lower()
            return name
    raise ValueError("No H1 heading found")


def _parse_datasets(lines: list[str]) -> list[DatasetValidationSpec]:
    datasets: list[DatasetValidationSpec] = []
    current_name: str | None = None
    current_block: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            if current_name and current_block:
                datasets.append(_parse_single(current_name, current_block))
            current_name = stripped[3:].strip()
            current_block = []
        elif current_name is not None:
            current_block.append(line)

    if current_name and current_block:
        datasets.append(_parse_single(current_name, current_block))
    return datasets


def _parse_single(name: str, block: list[str]) -> DatasetValidationSpec:
    date_range_start = ""
    expected_row_count = ""
    null_tolerances: list[NullToleranceSpec] = []
    completeness_dimensions: list[str] = []
    completeness_frequency = "monthly"
    staleness_months = 3

    in_null_table = False
    for line in block:
        stripped = line.strip()

        if in_null_table:
            if stripped.startswith("|") and not stripped.startswith("|--") and not stripped.startswith("| Column"):
                cells = [c.strip() for c in stripped.split("|") if c.strip()]
                if len(cells) >= 2:
                    try:
                        null_tolerances.append(NullToleranceSpec(
                            column=cells[0], max_null_pct=float(cells[1]),
                        ))
                    except ValueError:
                        pass
                continue
            elif stripped.startswith("|"):
                continue
            else:
                in_null_table = False

        if "**Null tolerance**" in stripped:
            in_null_table = True
            continue
        if "**Date range**" in stripped:
            match = re.search(r":\s*(\d{4}-\d{2})", stripped)
            if match:
                date_range_start = match.group(1)
        elif "**Expected row count**" in stripped:
            match = re.search(r":\s*(.*)", stripped)
            if match:
                expected_row_count = match.group(1).strip()
        elif "**Completeness**" in stripped:
            dim_match = re.search(r"Every\s+(\w+)", stripped)
            if dim_match:
                completeness_dimensions = [dim_match.group(1)]
            freq_match = re.search(r"every\s+(month|quarter|year|week|day)", stripped, re.IGNORECASE)
            if freq_match:
                completeness_frequency = freq_match.group(1).lower() + "ly"
        elif "**Staleness**" in stripped:
            months_match = re.search(r"within\s+(\d+)\s+months?", stripped)
            if months_match:
                staleness_months = int(months_match.group(1))

    return DatasetValidationSpec(
        name=name,
        date_range_start=date_range_start,
        null_tolerances=null_tolerances,
        expected_row_count=expected_row_count,
        completeness_dimensions=completeness_dimensions,
        completeness_frequency=completeness_frequency,
        staleness_months=staleness_months,
    )
```

- [ ] **Step 4: Write the audit_rules SQL template**

```jinja2
{# src/energy_usa/generators/templates/audit_rules.sql.j2 #}
-- Validation rules for {{ source }} datasets.
-- Generated from specs/validate/{{ source }}.md
-- Run against the ingest database to seed quality.audit_rules.

{% for ds in datasets %}
-- {{ ds.name }}
{% for nt in ds.null_tolerances %}
INSERT INTO quality.audit_rules (rule_id, source, dataset, check_type, column_name, threshold, enabled)
VALUES ('{{ source }}.{{ ds.name }}.null_rate.{{ nt.column }}', '{{ source }}', '{{ ds.name }}', 'null_rate', '{{ nt.column }}', '{"max_null_pct": {{ nt.max_null_pct }}}', true)
ON CONFLICT (rule_id) DO UPDATE SET threshold = EXCLUDED.threshold, enabled = EXCLUDED.enabled;
{% endfor %}
{% if ds.staleness_months %}
INSERT INTO quality.audit_rules (rule_id, source, dataset, check_type, column_name, threshold, enabled)
VALUES ('{{ source }}.{{ ds.name }}.staleness', '{{ source }}', '{{ ds.name }}', 'staleness', NULL, '{"max_months_behind": {{ ds.staleness_months }}}', true)
ON CONFLICT (rule_id) DO UPDATE SET threshold = EXCLUDED.threshold, enabled = EXCLUDED.enabled;
{% endif %}
{% if ds.completeness_dimensions %}
INSERT INTO quality.audit_rules (rule_id, source, dataset, check_type, column_name, threshold, enabled)
VALUES ('{{ source }}.{{ ds.name }}.completeness', '{{ source }}', '{{ ds.name }}', 'completeness', NULL, '{"dimensions": {{ ds.completeness_dimensions | tojson }}, "frequency": "{{ ds.completeness_frequency }}"}', true)
ON CONFLICT (rule_id) DO UPDATE SET threshold = EXCLUDED.threshold, enabled = EXCLUDED.enabled;
{% endif %}
{% if ds.expected_row_count %}
INSERT INTO quality.audit_rules (rule_id, source, dataset, check_type, column_name, threshold, enabled)
VALUES ('{{ source }}.{{ ds.name }}.row_count', '{{ source }}', '{{ ds.name }}', 'row_count', NULL, '{{ ds.expected_row_count | tojson }}', true)
ON CONFLICT (rule_id) DO UPDATE SET threshold = EXCLUDED.threshold, enabled = EXCLUDED.enabled;
{% endif %}

{% endfor %}
```

- [ ] **Step 5: Write the generator**

```python
# src/energy_usa/generators/validate.py
"""Generate audit_rules SQL from a parsed validate spec."""

from __future__ import annotations

from pathlib import Path

import jinja2

from energy_usa.generators.models_validate import ValidateSpec

TEMPLATES_DIR = Path(__file__).parent / "templates"


def generate_validate(
    spec: ValidateSpec,
    *,
    output_dir: Path | None = None,
) -> list[Path]:
    """Generate audit_rules seed SQL from a validate spec.

    :param spec: Parsed validate spec.
    :param output_dir: Root directory (defaults to cwd).
    :returns: List of generated file paths.
    """
    root = output_dir or Path.cwd()
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
        keep_trailing_newline=True,
    )

    sql_path = root / "docker" / "postgres" / "init" / "ingest" / spec.source / "audit_rules.sql"
    sql_path.parent.mkdir(parents=True, exist_ok=True)

    rendered = env.get_template("audit_rules.sql.j2").render(
        source=spec.source,
        datasets=spec.datasets,
    )
    sql_path.write_text(rendered)
    return [sql_path]
```

- [ ] **Step 6: Write generator test**

```python
# tests/unit/generators/test_validate_gen.py
"""Tests for the validate spec generator."""
import textwrap
from pathlib import Path

from energy_usa.generators.parse_validate import parse_validate_spec
from energy_usa.generators.validate import generate_validate


SPEC = textwrap.dedent("""\
    # EIA Validation Rules

    ## retail_sales
    - **Date range**: 2001-01 to present
    - **Null tolerance**:
      | Column | Max null % |
      |--------|-----------|
      | revenue | 5 |
      | price | 5 |
    - **Completeness**: Every stateid should have data for every month
    - **Staleness**: Most recent period within 3 months of today
""")


def test_generates_audit_rules_sql(tmp_path):
    spec = parse_validate_spec(SPEC)
    paths = generate_validate(spec, output_dir=tmp_path)
    assert len(paths) == 1
    sql_file = tmp_path / "docker" / "postgres" / "init" / "ingest" / "eia" / "audit_rules.sql"
    assert sql_file.exists()
    content = sql_file.read_text()
    assert "quality.audit_rules" in content


def test_null_rate_rules_generated(tmp_path):
    spec = parse_validate_spec(SPEC)
    generate_validate(spec, output_dir=tmp_path)
    content = (tmp_path / "docker" / "postgres" / "init" / "ingest" / "eia" / "audit_rules.sql").read_text()
    assert "eia.retail_sales.null_rate.revenue" in content
    assert "eia.retail_sales.null_rate.price" in content
    assert '"max_null_pct": 5' in content


def test_staleness_rule_generated(tmp_path):
    spec = parse_validate_spec(SPEC)
    generate_validate(spec, output_dir=tmp_path)
    content = (tmp_path / "docker" / "postgres" / "init" / "ingest" / "eia" / "audit_rules.sql").read_text()
    assert "eia.retail_sales.staleness" in content
    assert '"max_months_behind": 3' in content


def test_completeness_rule_generated(tmp_path):
    spec = parse_validate_spec(SPEC)
    generate_validate(spec, output_dir=tmp_path)
    content = (tmp_path / "docker" / "postgres" / "init" / "ingest" / "eia" / "audit_rules.sql").read_text()
    assert "eia.retail_sales.completeness" in content
    assert '"dimensions"' in content
    assert "stateid" in content


def test_on_conflict_upsert(tmp_path):
    spec = parse_validate_spec(SPEC)
    generate_validate(spec, output_dir=tmp_path)
    content = (tmp_path / "docker" / "postgres" / "init" / "ingest" / "eia" / "audit_rules.sql").read_text()
    assert "ON CONFLICT (rule_id) DO UPDATE" in content
```

- [ ] **Step 7: Run all tests**

```bash
uv run pytest tests/unit/generators/test_parse_validate.py tests/unit/generators/test_validate_gen.py -v
```

Expected: All pass.

- [ ] **Step 8: Commit**

```bash
git add src/energy_usa/generators/models_validate.py \
        src/energy_usa/generators/parse_validate.py \
        src/energy_usa/generators/validate.py \
        src/energy_usa/generators/templates/audit_rules.sql.j2 \
        tests/unit/generators/test_parse_validate.py \
        tests/unit/generators/test_validate_gen.py
git commit -m "add validate spec parser and audit_rules SQL generator

Parses specs/validate/<source>.md into ValidateSpec dataclasses.
Generates quality.audit_rules INSERT SQL via Jinja2 template.
Handles null_rate, staleness, completeness, and row_count rules."
```

---

## Task 5: Write EIA Validate Spec

Document quality expectations for the key EIA datasets.

**Files:**
- Create: `specs/validate/eia.md`

- [ ] **Step 1: Write the EIA validate spec**

Start with the most important datasets. Not all 35 need validation rules immediately — focus on the datasets that have meaningful quality expectations.

```markdown
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

## electric_power_operational
- **Date range**: 2001-01 to present
- **Null tolerance**:
  | Column | Max null % |
  |--------|-----------|
  | generation | 10 |
  | total_consumption | 15 |
- **Completeness**: Every stateid should have data for every month
- **Staleness**: Most recent period within 3 months of today

## state_source_disposition
- **Date range**: 2001-01 to present
- **Null tolerance**:
  | Column | Max null % |
  |--------|-----------|
  | generation | 10 |
- **Staleness**: Most recent period within 3 months of today

## state_summary
- **Date range**: 2001-01 to present
- **Staleness**: Most recent period within 18 months of today

## co2_emissions
- **Date range**: 1970-01 to present
- **Null tolerance**:
  | Column | Max null % |
  |--------|-----------|
  | value | 2 |
- **Staleness**: Most recent period within 24 months of today

## natural_gas_prices
- **Date range**: 1997-01 to present
- **Null tolerance**:
  | Column | Max null % |
  |--------|-----------|
  | value | 5 |
- **Staleness**: Most recent period within 3 months of today

## petroleum_prices
- **Date range**: 1995-01 to present
- **Null tolerance**:
  | Column | Max null % |
  |--------|-----------|
  | value | 5 |
- **Staleness**: Most recent period within 3 months of today

## total_energy
- **Date range**: 1973-01 to present
- **Null tolerance**:
  | Column | Max null % |
  |--------|-----------|
  | value | 5 |
- **Staleness**: Most recent period within 6 months of today

## seds
- **Date range**: 1960-01 to present
- **Null tolerance**:
  | Column | Max null % |
  |--------|-----------|
  | value | 10 |
- **Staleness**: Most recent period within 24 months of today
```

- [ ] **Step 2: Verify the spec parses and generates SQL**

```bash
uv run python -c "
from energy_usa.generators.parse_validate import parse_validate_spec
from energy_usa.generators.validate import generate_validate
from pathlib import Path

spec = parse_validate_spec(Path('specs/validate/eia.md').read_text())
print(f'Parsed {len(spec.datasets)} datasets')
for ds in spec.datasets:
    rules = len(ds.null_tolerances) + (1 if ds.staleness_months else 0) + (1 if ds.completeness_dimensions else 0)
    print(f'  {ds.name}: {rules} rules')

paths = generate_validate(spec, output_dir=Path('/tmp/validate-test'))
print(f'Generated: {paths[0]}')
print(Path(paths[0]).read_text()[:500])
"
```

Expected: 9 datasets parsed, SQL generated with INSERT statements.

- [ ] **Step 3: Commit**

```bash
git add specs/validate/eia.md
git commit -m "add EIA validate spec for 9 key datasets

Quality expectations for retail_sales, electric_power_operational,
state_source_disposition, state_summary, co2_emissions, natural_gas_prices,
petroleum_prices, total_energy, and seds. Covers null rates, staleness,
and completeness checks."
```

---

## Task 6: CLI, Makefile, and Superset Seed

Add validation CLI, Makefile targets, and Superset dataset for quality tables.

**Files:**
- Create: `scripts/validate.py`
- Modify: `scripts/generate.py`
- Modify: `Makefile`
- Modify: `docker/superset/seed_databases.py`

- [ ] **Step 1: Create validation CLI script**

```python
#!/usr/bin/env -S uv run python
# scripts/validate.py
"""CLI for running validation flows and viewing audit results.

Usage:
    uv run python scripts/validate.py run --source eia
    uv run python scripts/validate.py run --source eia --dataset retail_sales
    uv run python scripts/validate.py audit --source eia
    uv run python scripts/validate.py audit --source eia --dataset retail_sales
"""
import argparse
import sys

from energy_usa.config import Settings
from energy_usa.db.connection import get_connection


def cmd_run(args: argparse.Namespace) -> None:
    """Run validation flow."""
    from energy_usa.flows.validate.eia import validate_eia
    datasets = [args.dataset] if args.dataset else None
    summary = validate_eia(datasets=datasets)
    total = sum(summary.values())
    print(f"\nValidation complete: {total} checks")
    for status, count in sorted(summary.items()):
        if count > 0:
            print(f"  {status}: {count}")
    if summary.get("fail", 0) > 0:
        sys.exit(1)


def cmd_audit(args: argparse.Namespace) -> None:
    """Show recent audit results."""
    settings = Settings()
    conn = get_connection(settings.ingest_database_url)
    try:
        if args.dataset:
            sql = """
            SELECT ar.rule_id, ar.status, ar.detail, ar.checked_at
            FROM quality.audit_results ar
            JOIN quality.audit_rules rl ON ar.rule_id = rl.rule_id
            WHERE rl.source = %(source)s AND rl.dataset = %(dataset)s
            ORDER BY ar.checked_at DESC
            LIMIT 50
            """
            params = {"source": args.source, "dataset": args.dataset}
        else:
            sql = """
            SELECT rl.dataset,
                   count(*) FILTER (WHERE ar.status = 'pass') AS pass,
                   count(*) FILTER (WHERE ar.status = 'fail') AS fail,
                   count(*) FILTER (WHERE ar.status = 'warn') AS warn,
                   count(*) FILTER (WHERE ar.status = 'error') AS error,
                   max(ar.checked_at) AS last_run
            FROM quality.audit_results ar
            JOIN quality.audit_rules rl ON ar.rule_id = rl.rule_id
            WHERE rl.source = %(source)s
            GROUP BY rl.dataset
            ORDER BY rl.dataset
            """
            params = {"source": args.source}

        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

        if not rows:
            print("No audit results found.")
            return

        if args.dataset:
            for row in rows:
                status = row["status"].upper()
                detail = row["detail"] or ""
                print(f"  [{status}] {row['rule_id']}  {detail}")
        else:
            print(f"{'Dataset':<30} {'Pass':>5} {'Fail':>5} {'Warn':>5} {'Error':>6}  Last Run")
            print("-" * 85)
            for row in rows:
                print(
                    f"{row['dataset']:<30} {row['pass']:>5} {row['fail']:>5} "
                    f"{row['warn']:>5} {row['error']:>6}  {row['last_run']}"
                )
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run validation and view audit results")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Run validation checks")
    run_parser.add_argument("--source", default="eia", help="Source name")
    run_parser.add_argument("--dataset", help="Single dataset (optional)")

    audit_parser = sub.add_parser("audit", help="View audit results")
    audit_parser.add_argument("--source", default="eia", help="Source name")
    audit_parser.add_argument("--dataset", help="Single dataset (optional)")

    args = parser.parse_args()
    if args.command == "run":
        cmd_run(args)
    elif args.command == "audit":
        cmd_audit(args)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Add validate subcommand to scripts/generate.py**

Add a `validate` subcommand that generates audit_rules SQL from the validate spec:

```python
def cmd_validate(args: argparse.Namespace) -> None:
    spec_path = Path("specs/validate") / f"{args.source}.md"
    if not spec_path.exists():
        print(f"ERROR: Spec file not found: {spec_path}")
        sys.exit(1)
    from energy_usa.generators.parse_validate import parse_validate_spec
    from energy_usa.generators.validate import generate_validate
    spec = parse_validate_spec(spec_path.read_text())
    generated = generate_validate(spec)
    for path in generated:
        print(f"  Generated: {path}")
    print(f"\n{len(generated)} files generated from specs/validate/{args.source}.md")
```

Add the subparser in `main()`:
```python
    validate_parser = sub.add_parser("validate", help="Generate validate audit rules SQL")
    validate_parser.add_argument("--source", required=True, help="Source name")
```

And add the dispatch:
```python
    elif args.command == "validate":
        cmd_validate(args)
```

- [ ] **Step 3: Add Makefile targets**

Add variables and targets:

```makefile
VSOURCE   ?= eia                    # Source for validation
VDATASET  ?=                        # Dataset for validation (blank = all)
```

```makefile
# ── Validation ────────────────────────────────────────────────────────────────
# Run data quality checks against ingested data.
#
# Examples:
#   make validate SOURCE=eia
#   make validate SOURCE=eia VDATASET=retail_sales
#   make audit SOURCE=eia

validate:  ## Run validation checks. Use VSOURCE, VDATASET (optional).
	uv run python scripts/validate.py run \
	  --source $(VSOURCE) \
	  $(if $(VDATASET),--dataset $(VDATASET))

audit:  ## Show audit results summary. Use VSOURCE, VDATASET (optional).
	uv run python scripts/validate.py audit \
	  --source $(VSOURCE) \
	  $(if $(VDATASET),--dataset $(VDATASET))

generate-validate:  ## Generate validate audit rules SQL from specs/validate/<SOURCE>.md
	uv run python scripts/generate.py validate --source $(VSOURCE)
```

Update `.PHONY` to include `validate audit generate-validate`.

- [ ] **Step 4: Add quality tables to Superset seed**

Add to the DATASETS list in `docker/superset/seed_databases.py`:

```python
    ("quality", "audit_rules"),
    ("quality", "audit_results"),
```

- [ ] **Step 5: Commit**

```bash
git add scripts/validate.py scripts/generate.py Makefile docker/superset/seed_databases.py
git commit -m "add validation CLI, Makefile targets, and Superset quality datasets

make validate runs checks, make audit shows results, make generate-validate
produces audit_rules SQL. Superset can now browse quality.audit_results."
```

---

## Task 7: Update Documentation

Update CLAUDE.md with validation commands and quality schema info.

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add validation commands to CLAUDE.md**

In the Common Commands section, add:

```markdown
# Validation (data quality checks)
make validate VSOURCE=eia                          # Run all EIA checks
make validate VSOURCE=eia VDATASET=retail_sales    # Single dataset
make audit VSOURCE=eia                             # View results summary
make generate-validate VSOURCE=eia                 # Generate audit rules SQL
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "document validation commands in CLAUDE.md"
```

---

## Task 8: End-to-End Verification

Verify everything works together.

**Files:** None — verification only.

- [ ] **Step 1: Run all tests**

```bash
uv run pytest tests/ -v --ignore=tests/integration
```

Expected: All pass.

- [ ] **Step 2: Verify all imports**

```bash
uv run python -c "
from energy_usa.db.quality.audit import AuditRule, AuditResult, load_rules, write_result, upsert_rules
from energy_usa.db.quality.checks import run_check, check_null_rate, check_staleness, check_row_count, check_range, check_completeness
from energy_usa.flows.validate.eia import validate_eia
from energy_usa.generators.parse_validate import parse_validate_spec
from energy_usa.generators.validate import generate_validate
print('All validation imports OK')
"
```

Expected: `All validation imports OK`

- [ ] **Step 3: Verify spec parses and generates SQL**

```bash
uv run python -c "
from pathlib import Path
from energy_usa.generators.parse_validate import parse_validate_spec
from energy_usa.generators.validate import generate_validate

spec = parse_validate_spec(Path('specs/validate/eia.md').read_text())
print(f'{len(spec.datasets)} datasets in validate spec')

paths = generate_validate(spec, output_dir=Path('/tmp/val-verify'))
content = Path(paths[0]).read_text()
rule_count = content.count('INSERT INTO quality.audit_rules')
print(f'{rule_count} audit rules generated')
print('Validation system OK')
"
```

- [ ] **Step 4: Commit any fixes**

If issues found, fix and commit.
