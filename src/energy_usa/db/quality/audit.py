"""Database operations for the quality audit schema.

This module provides dataclasses that represent rows in quality.audit_rules and
quality.audit_results, along with three functions that read from / write to those
tables.

The quality schema is the backbone of the validation system:
- ``quality.audit_rules`` defines *what* to check (one row per check).
- ``quality.audit_results`` records *the outcome* of each check run.

Typical call sequence inside a validation flow::

    from energy_usa.db.quality.audit import load_rules, write_result

    rules = load_rules(conn, source="eia", datasets=["retail_sales"])
    for rule in rules:
        result = run_check(conn, rule, run_id="abc-123")
        write_result(conn, result)
"""

import json
from dataclasses import dataclass, field
from typing import Any

import psycopg


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class AuditRule:
    """One row from ``quality.audit_rules``.

    :param rule_id: Unique identifier for the rule, e.g. ``"eia.retail_sales.null_rate"``.
    :param source: Data source namespace, e.g. ``"eia"``.
    :param dataset: Dataset name within the source, e.g. ``"retail_sales"``.
    :param check_type: The kind of check to run. Must match a key understood by
        :func:`energy_usa.db.quality.checks.run_check` — e.g. ``"null_rate"``,
        ``"staleness"``, ``"row_count"``, ``"range"``, ``"completeness"``.
    :param column_name: The column targeted by the check, or ``None`` for checks
        that operate on the whole table (staleness, row_count, completeness).
    :param threshold: A dict of check-specific parameters. For example a
        ``null_rate`` rule might use ``{"max_null_pct": 5.0}``.
    :param enabled: When ``False`` the rule is skipped by :func:`load_rules`.
    """

    rule_id: str
    source: str
    dataset: str
    check_type: str
    column_name: str | None
    threshold: dict[str, Any]
    enabled: bool = True

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------

    @property
    def table_name(self) -> str:
        """Return the fully-qualified table name as ``"{source}.{dataset}"``.

        This is used in SQL f-strings inside the check functions.  The value
        comes from the audit_rules table (controlled data), not from user input,
        so using it in an f-string is safe.

        :returns: Schema-qualified table name, e.g. ``"eia.retail_sales"``.
        """
        return f"{self.source}.{self.dataset}"

    # ------------------------------------------------------------------
    # Constructor helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "AuditRule":
        """Build an :class:`AuditRule` from a database row dict.

        Handles the case where ``threshold`` arrives as a JSON string (e.g.
        when coming from a plain ``psycopg`` cursor that does not automatically
        decode JSONB) vs. already being a Python dict (psycopg3 with the
        default JSONB decoder).

        :param row: A dict whose keys match the ``quality.audit_rules`` columns.
        :returns: A fully populated :class:`AuditRule` instance.
        """
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
            enabled=bool(row.get("enabled", True)),
        )


@dataclass
class AuditResult:
    """One row to be written to ``quality.audit_results``.

    :param rule_id: Foreign key back to ``quality.audit_rules.rule_id``.
    :param run_id: An arbitrary string that groups all results from a single
        validation flow run together (e.g. a Prefect flow-run ID or a UUID).
    :param status: One of ``"pass"``, ``"fail"``, ``"warn"``, or ``"error"``.
        ``"error"`` means the check itself raised an exception and could not
        produce a meaningful measurement.
    :param measured_value: A free-form dict of numbers / strings that describe
        what was actually observed, e.g. ``{"null_pct": 3.2, "total": 1000}``.
        May be ``None`` when the check errored before producing a measurement.
    :param detail: A human-readable explanation of why the check failed or
        errored, or ``None`` for passing results.
    """

    rule_id: str
    run_id: str
    status: str
    measured_value: dict[str, Any] | None = field(default=None)
    detail: str | None = field(default=None)

    @property
    def is_pass(self) -> bool:
        """Return ``True`` only when status is ``"pass"``.

        :returns: Boolean indicating a clean result.
        """
        return self.status == "pass"


# ---------------------------------------------------------------------------
# Database functions
# ---------------------------------------------------------------------------


def load_rules(
    conn: psycopg.Connection,
    *,
    source: str,
    datasets: list[str] | None = None,
) -> list[AuditRule]:
    """Fetch enabled audit rules from ``quality.audit_rules``.

    Filters by ``source`` and optionally by a list of dataset names.  Only
    rules where ``enabled = true`` are returned.

    :param conn: An open psycopg connection (dict row factory recommended).
    :param source: The source namespace to filter on, e.g. ``"eia"``.
    :param datasets: Optional list of dataset names.  When provided, only rules
        for those datasets are returned.  Useful for running validation on a
        single freshly-ingested dataset rather than the whole source.
    :returns: A list of :class:`AuditRule` instances, possibly empty.
    """
    sql = """
        SELECT rule_id, source, dataset, check_type, column_name, threshold, enabled
        FROM quality.audit_rules
        WHERE source = %(source)s
          AND enabled = true
    """
    params: dict[str, Any] = {"source": source}

    if datasets is not None:
        sql += " AND dataset = ANY(%(datasets)s)"
        params["datasets"] = datasets

    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    return [AuditRule.from_dict(row) for row in rows]


def write_result(conn: psycopg.Connection, result: AuditResult) -> None:
    """Insert one :class:`AuditResult` into ``quality.audit_results``.

    The ``measured_value`` dict is serialised to JSON before insertion because
    psycopg may not handle bare Python dicts for JSONB columns in all
    configurations.

    :param conn: An open psycopg connection.
    :param result: The audit result to persist.
    """
    sql = """
        INSERT INTO quality.audit_results (rule_id, run_id, status, measured_value, detail)
        VALUES (%(rule_id)s, %(run_id)s, %(status)s, %(measured_value)s, %(detail)s)
    """
    measured_json = (
        json.dumps(result.measured_value) if result.measured_value is not None else None
    )
    with conn.cursor() as cur:
        cur.execute(
            sql,
            {
                "rule_id": result.rule_id,
                "run_id": result.run_id,
                "status": result.status,
                "measured_value": measured_json,
                "detail": result.detail,
            },
        )
    conn.commit()


def upsert_rules(conn: psycopg.Connection, rules: list[AuditRule]) -> int:
    """Insert or update a list of :class:`AuditRule` objects in ``quality.audit_rules``.

    On conflict on ``rule_id`` the existing row is updated with the values from
    the incoming rule (everything except ``created_at``).

    This is useful for seeding or refreshing rules from a YAML/JSON config file
    without worrying about whether the rule already exists.

    :param conn: An open psycopg connection.
    :param rules: The rules to upsert.
    :returns: The number of rules processed (not necessarily changed).
    """
    if not rules:
        return 0

    sql = """
        INSERT INTO quality.audit_rules
            (rule_id, source, dataset, check_type, column_name, threshold, enabled)
        VALUES
            (%(rule_id)s, %(source)s, %(dataset)s, %(check_type)s,
             %(column_name)s, %(threshold)s, %(enabled)s)
        ON CONFLICT (rule_id) DO UPDATE SET
            source      = EXCLUDED.source,
            dataset     = EXCLUDED.dataset,
            check_type  = EXCLUDED.check_type,
            column_name = EXCLUDED.column_name,
            threshold   = EXCLUDED.threshold,
            enabled     = EXCLUDED.enabled
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
