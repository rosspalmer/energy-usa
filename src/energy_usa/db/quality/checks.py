"""Generic SQL check functions for the quality validation system.

Each function receives an open database connection, an :class:`AuditRule`, and a
``run_id`` string, then returns an :class:`AuditResult` describing whether the
check passed, failed, warned, or errored.

**SQL injection note**: Table and column names in SQL are built from
:attr:`AuditRule.table_name` and :attr:`AuditRule.column_name`.  These values
come from the ``quality.audit_rules`` table, which is managed by the project
team — not by end users.  Using f-strings for schema-controlled identifiers is
intentional and safe; dynamic *values* (periods, thresholds, etc.) are always
passed via parameterised SQL (``%(name)s`` placeholders).

Supported check types (value of ``rule.check_type``):

- ``"null_rate"``    — fraction of NULLs in a column must stay below a threshold
- ``"staleness"``   — most recent ``period`` date must be recent enough
- ``"row_count"``   — row counts per period must stay within a range
- ``"range"``       — min/max of a column must stay within bounds
- ``"completeness"``— every combination of dimensions × periods must be present
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import psycopg

from energy_usa.db.quality.audit import AuditResult, AuditRule

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


_CHECK_REGISTRY: dict[str, Any] = {}


def run_check(conn: psycopg.Connection, rule: AuditRule, run_id: str) -> AuditResult:
    """Dispatch to the correct check function based on ``rule.check_type``.

    Catches any unexpected exception from the underlying check and converts it
    to an ``"error"`` result rather than crashing the caller.  This lets a
    validation flow continue through all rules even if one check function
    breaks.

    :param conn: An open psycopg connection.
    :param rule: The rule that describes what to check.
    :param run_id: Identifier tying this result to the current validation run.
    :returns: An :class:`AuditResult` with status ``"pass"``, ``"fail"``,
        ``"warn"``, or ``"error"``.
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
            detail=f"Unknown check_type: '{rule.check_type}'",
        )

    try:
        return fn(conn, rule, run_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("check %s raised an exception", rule.rule_id)
        return AuditResult(
            rule_id=rule.rule_id,
            run_id=run_id,
            status="error",
            detail=f"{type(exc).__name__}: {exc}",
        )


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------


def check_null_rate(
    conn: psycopg.Connection, rule: AuditRule, run_id: str
) -> AuditResult:
    """Check that the fraction of NULL values in a column is below a threshold.

    Threshold keys:
    - ``max_null_pct`` (float) — maximum acceptable percentage of NULLs, e.g. ``5.0``.

    Returns ``"warn"`` when the table is empty (can't compute a meaningful rate),
    ``"pass"`` when null_pct ≤ max_null_pct, and ``"fail"`` otherwise.

    :param conn: An open psycopg connection.
    :param rule: Must have ``column_name`` set and ``threshold["max_null_pct"]``.
    :param run_id: Validation run identifier.
    :returns: An :class:`AuditResult`.
    """
    col = rule.column_name
    table = rule.table_name
    max_null_pct = float(rule.threshold["max_null_pct"])

    # Table/column identifiers come from audit_rules (project-managed) — f-string is safe.
    sql = f"""
        SELECT
            count(*) AS total,
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
            rule_id=rule.rule_id,
            run_id=run_id,
            status="warn",
            measured_value={"total": 0, "nulls": 0, "null_pct": None},
            detail="Table is empty — cannot compute null rate.",
        )

    null_pct = round(nulls / total * 100, 4)
    measured = {"total": total, "nulls": nulls, "null_pct": null_pct}

    if null_pct <= max_null_pct:
        return AuditResult(
            rule_id=rule.rule_id,
            run_id=run_id,
            status="pass",
            measured_value=measured,
        )
    return AuditResult(
        rule_id=rule.rule_id,
        run_id=run_id,
        status="fail",
        measured_value=measured,
        detail=(
            f"null rate {null_pct}% in column '{col}' "
            f"exceeds threshold {max_null_pct}%"
        ),
    )


def check_staleness(
    conn: psycopg.Connection, rule: AuditRule, run_id: str
) -> AuditResult:
    """Check that the most recent ``period`` date is not too far in the past.

    Threshold keys:
    - ``max_months_behind`` (int) — how many months behind today is acceptable.

    "Months behind" is computed as
    ``(today.year - max_period.year) * 12 + (today.month - max_period.month)``.

    :param conn: An open psycopg connection.
    :param rule: Must have ``threshold["max_months_behind"]``.
    :param run_id: Validation run identifier.
    :returns: An :class:`AuditResult`.
    """
    table = rule.table_name
    max_months = int(rule.threshold["max_months_behind"])

    sql = f"SELECT max(period) AS max_period FROM {table}"  # noqa: S608 — table is project-controlled
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()

    max_period = row["max_period"] if row else None

    if max_period is None:
        return AuditResult(
            rule_id=rule.rule_id,
            run_id=run_id,
            status="fail",
            measured_value={"max_period": None},
            detail="Table has no data — cannot check staleness.",
        )

    today = date.today()
    months_behind = (today.year - max_period.year) * 12 + (
        today.month - max_period.month
    )
    measured = {
        "max_period": str(max_period),
        "months_behind": months_behind,
        "max_months_behind": max_months,
    }

    if months_behind <= max_months:
        return AuditResult(
            rule_id=rule.rule_id,
            run_id=run_id,
            status="pass",
            measured_value=measured,
        )
    return AuditResult(
        rule_id=rule.rule_id,
        run_id=run_id,
        status="fail",
        measured_value=measured,
        detail=(
            f"Most recent period {max_period} is {months_behind} months behind; "
            f"threshold is {max_months}."
        ),
    )


def check_row_count(
    conn: psycopg.Connection, rule: AuditRule, run_id: str
) -> AuditResult:
    """Check that recent months each contain a plausible number of rows.

    Looks at the 12 most recent periods and verifies that each falls within
    ``[min_per_month, max_per_month]``.

    Threshold keys:
    - ``min_per_month`` (int) — minimum acceptable rows per period.
    - ``max_per_month`` (int) — maximum acceptable rows per period.

    :param conn: An open psycopg connection.
    :param rule: Must have ``threshold["min_per_month"]`` and
        ``threshold["max_per_month"]``.
    :param run_id: Validation run identifier.
    :returns: An :class:`AuditResult`.
    """
    table = rule.table_name
    min_per = int(rule.threshold["min_per_month"])
    max_per = int(rule.threshold["max_per_month"])

    sql = f"""
        SELECT period, count(*) AS cnt
        FROM {table}
        GROUP BY period
        ORDER BY period DESC
        LIMIT 12
    """  # noqa: S608 — table is project-controlled
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

    if not rows:
        return AuditResult(
            rule_id=rule.rule_id,
            run_id=run_id,
            status="fail",
            measured_value={"periods_checked": 0},
            detail="Table has no data — cannot check row counts.",
        )

    violations = [
        {"period": str(r["period"]), "count": r["cnt"]}
        for r in rows
        if not (min_per <= r["cnt"] <= max_per)
    ]

    measured: dict[str, Any] = {
        "periods_checked": len(rows),
        "min_per_month": min_per,
        "max_per_month": max_per,
        "violations": violations,
    }

    if not violations:
        return AuditResult(
            rule_id=rule.rule_id,
            run_id=run_id,
            status="pass",
            measured_value=measured,
        )
    return AuditResult(
        rule_id=rule.rule_id,
        run_id=run_id,
        status="fail",
        measured_value=measured,
        detail=(
            f"{len(violations)} period(s) outside range "
            f"[{min_per}, {max_per}]: "
            + ", ".join(f"{v['period']}={v['count']}" for v in violations)
        ),
    )


def check_range(
    conn: psycopg.Connection, rule: AuditRule, run_id: str
) -> AuditResult:
    """Check that a numeric column's values stay within expected bounds.

    Threshold keys:
    - ``min`` (float) — minimum acceptable value (inclusive).
    - ``max`` (float) — maximum acceptable value (inclusive).

    The column checked is ``rule.column_name`` (or ``threshold["column"]`` as
    a fallback for backward-compatibility).

    :param conn: An open psycopg connection.
    :param rule: Must have ``threshold["min"]`` and ``threshold["max"]``.
    :param run_id: Validation run identifier.
    :returns: An :class:`AuditResult`.
    """
    table = rule.table_name
    # Accept column from rule field or threshold dict for flexibility
    col = rule.column_name or rule.threshold.get("column")
    t_min = float(rule.threshold["min"])
    t_max = float(rule.threshold["max"])

    sql = f"""
        SELECT min({col}) AS min_val, max({col}) AS max_val
        FROM {table}
    """  # noqa: S608 — table/column are project-controlled
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()

    actual_min = row["min_val"]
    actual_max = row["max_val"]

    if actual_min is None and actual_max is None:
        return AuditResult(
            rule_id=rule.rule_id,
            run_id=run_id,
            status="fail",
            measured_value={"min_val": None, "max_val": None},
            detail="Table is empty — cannot check range.",
        )

    measured = {
        "min_val": actual_min,
        "max_val": actual_max,
        "threshold_min": t_min,
        "threshold_max": t_max,
    }

    failures = []
    if actual_min is not None and actual_min < t_min:
        failures.append(f"min {actual_min} < threshold {t_min}")
    if actual_max is not None and actual_max > t_max:
        failures.append(f"max {actual_max} > threshold {t_max}")

    if not failures:
        return AuditResult(
            rule_id=rule.rule_id,
            run_id=run_id,
            status="pass",
            measured_value=measured,
        )
    return AuditResult(
        rule_id=rule.rule_id,
        run_id=run_id,
        status="fail",
        measured_value=measured,
        detail=f"Column '{col}' out of range: " + "; ".join(failures),
    )


def check_completeness(
    conn: psycopg.Connection, rule: AuditRule, run_id: str
) -> AuditResult:
    """Check that no (dimension × period) combinations are missing.

    Cross-joins all distinct dimension values against all distinct periods and
    counts how many combinations are missing in the actual table.

    Threshold keys:
    - ``dimensions`` (list[str]) — column name(s) to treat as categorical
      dimensions, e.g. ``["stateid"]`` or ``["stateid", "sectorid"]``.
    - ``frequency`` (str) — currently informational; ``"monthly"`` or
      ``"annual"``.  May be used by future logic to filter expected periods.

    :param conn: An open psycopg connection.
    :param rule: Must have ``threshold["dimensions"]``.
    :param run_id: Validation run identifier.
    :returns: An :class:`AuditResult`; passes only when ``gap_count == 0``.
    """
    table = rule.table_name
    dims: list[str] = rule.threshold["dimensions"]

    # Build SELECT list for dimensions — identifiers from project-controlled data
    dim_select = ", ".join(f"d.{d}" for d in dims)
    dim_cross_select = ", ".join(f"{d}" for d in dims)

    # Subquery: cross join distinct dimension combos × distinct periods
    # then left-join actual data to find gaps.
    dim_subquery = " CROSS JOIN ".join(
        f"(SELECT DISTINCT {d} FROM {table}) AS dim_{d}" for d in dims
    )
    dim_join_cond = " AND ".join(f"actual.{d} = d.{d}" for d in dims)

    sql = f"""
        WITH dims AS (
            SELECT {dim_select}
            FROM {dim_subquery}
        ),
        periods AS (
            SELECT DISTINCT period FROM {table}
        ),
        expected AS (
            SELECT d.*, p.period
            FROM dims d CROSS JOIN periods p
        ),
        gaps AS (
            SELECT expected.*
            FROM expected
            LEFT JOIN {table} AS actual
                ON actual.period = expected.period
                AND {dim_join_cond}
            WHERE actual.period IS NULL
        )
        SELECT count(*) AS gap_count FROM gaps
    """  # noqa: S608 — all identifiers are project-controlled
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()

    gap_count = row["gap_count"]
    measured = {"gap_count": gap_count, "dimensions": dims}

    if gap_count == 0:
        return AuditResult(
            rule_id=rule.rule_id,
            run_id=run_id,
            status="pass",
            measured_value=measured,
        )
    return AuditResult(
        rule_id=rule.rule_id,
        run_id=run_id,
        status="fail",
        measured_value=measured,
        detail=(
            f"{gap_count} missing (dimension × period) combinations "
            f"for dimensions {dims}."
        ),
    )
