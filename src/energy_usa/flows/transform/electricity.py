"""Prefect flow: transform electricity domain tables.

Reads from ingest DB (eia.* tables), aggregates, and writes to
transform DB (electricity.* tables). Each table is an independent task.
"""
from prefect import flow, task
from prefect.logging import get_run_logger

from energy_usa.config import Settings
from energy_usa.db.connection import get_connection
from energy_usa.db.transform.electricity.generation_mix import query_generation_mix, upsert_generation_mix
from energy_usa.db.transform.electricity.retail_by_state import query_retail_by_state, upsert_retail_by_state
from energy_usa.db.transform.electricity.state_monthly_balance import query_state_monthly_balance, upsert_state_monthly_balance


@task(name="transform-generation-mix")
def transform_generation_mix_task(ingest_url: str, transform_url: str) -> int:
    logger = get_run_logger()
    ingest_conn = get_connection(ingest_url)
    try:
        rows = query_generation_mix(ingest_conn)
        logger.info("Queried %d generation_mix rows from ingest", len(rows))
    finally:
        ingest_conn.close()
    transform_conn = get_connection(transform_url)
    try:
        count = upsert_generation_mix(transform_conn, rows)
        logger.info("Upserted %d rows into electricity.generation_mix", count)
        return count
    finally:
        transform_conn.close()


@task(name="transform-retail-by-state")
def transform_retail_by_state_task(ingest_url: str, transform_url: str) -> int:
    logger = get_run_logger()
    ingest_conn = get_connection(ingest_url)
    try:
        rows = query_retail_by_state(ingest_conn)
        logger.info("Queried %d retail_by_state rows from ingest", len(rows))
    finally:
        ingest_conn.close()
    transform_conn = get_connection(transform_url)
    try:
        count = upsert_retail_by_state(transform_conn, rows)
        logger.info("Upserted %d rows into electricity.retail_by_state", count)
        return count
    finally:
        transform_conn.close()


@task(name="transform-state-monthly-balance")
def transform_state_monthly_balance_task(ingest_url: str, transform_url: str) -> int:
    logger = get_run_logger()
    ingest_conn = get_connection(ingest_url)
    try:
        rows = query_state_monthly_balance(ingest_conn)
        logger.info("Queried %d state_monthly_balance rows from ingest", len(rows))
    finally:
        ingest_conn.close()
    transform_conn = get_connection(transform_url)
    try:
        count = upsert_state_monthly_balance(transform_conn, rows)
        logger.info("Upserted %d rows into electricity.state_monthly_balance", count)
        return count
    finally:
        transform_conn.close()


@flow(name="transform-electricity", timeout_seconds=3600)
def transform_electricity(tables: list[str] | None = None) -> dict[str, int]:
    logger = get_run_logger()
    settings = Settings()
    if not settings.ingest_database_url:
        raise ValueError("INGEST_DATABASE_URL required")
    if not settings.transform_database_url:
        raise ValueError("TRANSFORM_DATABASE_URL required")

    all_tables = {
        "generation_mix": transform_generation_mix_task,
        "retail_by_state": transform_retail_by_state_task,
        "state_monthly_balance": transform_state_monthly_balance_task,
    }
    targets = all_tables if not tables else {k: v for k, v in all_tables.items() if k in tables}

    results = {}
    for name, task_fn in targets.items():
        logger.info("Transforming electricity.%s", name)
        count = task_fn(ingest_url=settings.ingest_database_url, transform_url=settings.transform_database_url)
        results[name] = count

    logger.info("Electricity transform complete: %s", results)
    return results
