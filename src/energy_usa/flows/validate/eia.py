"""Prefect flow to validate all EIA dataset quality rules.

This flow loads audit rules from ``quality.audit_rules``, runs each check
against the live ``eia.*`` tables, writes results to ``quality.audit_results``,
and returns a summary dict.

Typical invocation via Prefect UI or CLI::

    prefect deployment run validate-eia

Or locally for one-off checks::

    from energy_usa.flows.validate.eia import validate_eia
    asyncio.run(validate_eia(datasets=["retail_sales"]))

The flow is intentionally resilient: a check that raises an unhandled
exception is captured as an ``"error"`` result and does not abort the
rest of the run.  All rules are always attempted.
"""

from __future__ import annotations

import logging
from typing import Any

from prefect import flow, task
from prefect.logging import get_run_logger

from energy_usa.config import Settings
from energy_usa.db.connection import get_connection
from energy_usa.db.quality.audit import AuditResult, load_rules, write_result
from energy_usa.db.quality.checks import run_check

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


@task(name="run-validation-checks")
def run_validation_checks(
    database_url: str,
    run_id: str,
    datasets: list[str] | None,
) -> list[AuditResult]:
    """Load rules, run each check, persist results, and return all outcomes.

    Opens a single database connection for the entire task so that the
    overhead of connection setup is paid only once.  Each result is written
    immediately after its check completes so that partial results are
    preserved even if a later check fails catastrophically.

    :param database_url: Postgres connection URL for the ingest database.
    :param run_id: Identifier tying all results to this validation run.
        Typically the Prefect flow-run UUID; falls back to ``"manual"``.
    :param datasets: Optional list of dataset names to validate.  ``None``
        means validate all enabled EIA rules.
    :returns: List of :class:`~energy_usa.db.quality.audit.AuditResult`
        instances in the order the rules were fetched.
    """
    task_logger = get_run_logger()
    results: list[AuditResult] = []

    with get_connection(database_url) as conn:
        rules = load_rules(conn, source="eia", datasets=datasets)

        if not rules:
            task_logger.warning(
                "No enabled audit rules found for source='eia' (datasets=%s). "
                "Has audit_rules.sql been applied to the database?",
                datasets,
            )
            return results

        task_logger.info("Loaded %d rule(s) for source='eia'.", len(rules))

        for rule in rules:
            result = run_check(conn, rule, run_id)
            write_result(conn, result)
            results.append(result)

            # Log a single line per result so the task log is easy to scan.
            status_tag = result.status.upper()
            col_part = f".{rule.column_name}" if rule.column_name else ""
            detail_part = f" — {result.detail}" if result.detail else ""
            task_logger.info(
                "[%s] %s.%s%s %s%s",
                status_tag,
                rule.dataset,
                rule.check_type,
                col_part,
                "",
                detail_part,
            )

    return results


# ---------------------------------------------------------------------------
# Flow
# ---------------------------------------------------------------------------


@flow(name="validate-eia", timeout_seconds=3600)
def validate_eia(datasets: list[str] | None = None) -> dict[str, Any]:
    """Run all enabled EIA audit rules and return a summary.

    Steps:

    1. Load :class:`~energy_usa.config.Settings` and validate that
       ``INGEST_DATABASE_URL`` is set.
    2. Obtain the Prefect flow-run ID (falls back to ``"manual"`` when run
       outside Prefect).
    3. Delegate to :func:`run_validation_checks` (a Prefect task), which
       opens a DB connection, runs every rule, and writes each result.
    4. Summarise outcomes and log a final status line.

    :param datasets: Optional list of dataset names to validate, e.g.
        ``["retail_sales", "co2_emissions"]``.  When ``None`` all enabled
        EIA rules are run.
    :returns: A dict with keys ``run_id``, ``total``, ``pass``, ``fail``,
        ``warn``, ``error``, and ``datasets`` (the ``datasets`` argument).
    """
    flow_logger = get_run_logger()

    # --- Settings ------------------------------------------------------------
    settings = Settings()
    if not settings.ingest_database_url:
        raise ValueError(
            "INGEST_DATABASE_URL is not set. "
            "Copy .env.example to .env and configure the database URL."
        )

    # --- Prefect run ID (best-effort) ----------------------------------------
    try:
        from prefect.context import get_run_context  # noqa: PLC0415

        ctx = get_run_context()
        run_id = str(ctx.flow_run.id) if ctx and ctx.flow_run else "manual"
    except Exception:  # noqa: BLE001
        run_id = "manual"

    flow_logger.info(
        "Starting validate-eia run_id=%s datasets=%s", run_id, datasets
    )

    # --- Run checks (via Prefect task) ---------------------------------------
    results: list[AuditResult] = run_validation_checks(
        database_url=settings.ingest_database_url,
        run_id=run_id,
        datasets=datasets,
    )

    # --- Summarise -----------------------------------------------------------
    counts: dict[str, int] = {"pass": 0, "fail": 0, "warn": 0, "error": 0}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1

    total = len(results)
    flow_logger.info(
        "validate-eia complete: %d total — %d pass, %d fail, %d warn, %d error",
        total,
        counts["pass"],
        counts["fail"],
        counts["warn"],
        counts["error"],
    )

    return {
        "run_id": run_id,
        "total": total,
        "pass": counts["pass"],
        "fail": counts["fail"],
        "warn": counts["warn"],
        "error": counts["error"],
        "datasets": datasets,
    }
