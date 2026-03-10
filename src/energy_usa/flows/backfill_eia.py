"""Prefect flow to backfill EIA datasets in configurable month chunks.

The parent flow splits a date range (YYYY-MM to YYYY-MM) into chunks of N
months and submits one child ingest flow run per chunk. If date bounds are
omitted, it defaults to the same range behavior as ingest flows.
"""

import asyncio
from typing import Any, Awaitable, Callable, Literal

from prefect import flow
from prefect.logging import get_run_logger

from energy_usa.flows.date_range import monthly_chunks, resolve_date_range
from energy_usa.flows.eia_electric_power_operational import ingest_eia_electric_power_operational
from energy_usa.flows.eia_retail_sales import ingest_eia_retail_sales
from energy_usa.flows.eia_state_source_disposition import ingest_eia_state_source_disposition
from energy_usa.flows.eia_state_summary import ingest_eia_state_summary

DatasetName = Literal[
    "retail_sales",
    "electric_power_operational",
    "state_source_disposition",
    "state_summary",
    "all",
]

IngestFlow = Callable[..., Awaitable[int]]


def _get_ingest_flows(dataset: DatasetName) -> list[tuple[str, IngestFlow]]:
    """Resolve dataset selector to one or more ingest flow callables."""
    flow_map: dict[str, tuple[str, IngestFlow]] = {
        "retail_sales": ("retail_sales", ingest_eia_retail_sales),
        "electric_power_operational": (
            "electric_power_operational",
            ingest_eia_electric_power_operational,
        ),
        "state_source_disposition": (
            "state_source_disposition",
            ingest_eia_state_source_disposition,
        ),
        "state_summary": ("state_summary", ingest_eia_state_summary),
    }
    if dataset == "all":
        return [
            flow_map["retail_sales"],
            flow_map["electric_power_operational"],
            flow_map["state_source_disposition"],
            flow_map["state_summary"],
        ]
    if dataset not in flow_map:
        valid = ", ".join([*flow_map.keys(), "all"])
        raise ValueError(f"Invalid dataset '{dataset}'. Expected one of: {valid}")
    return [flow_map[dataset]]


@flow(name="backfill-eia", retries=1)
async def backfill_eia(
    date_start: str | None = None,
    date_end: str | None = None,
    chunk_months: int = 1,
    dataset: DatasetName = "retail_sales",
) -> dict[str, Any]:
    """Submit EIA backfill ingest runs in contiguous month chunks.

    :param date_start: Optional start period (YYYY-MM). Defaults to last calendar month.
    :param date_end: Optional end period (YYYY-MM). Defaults to current month.
    :param chunk_months: Number of months per child run; must be >= 1.
    :param dataset: Dataset selector or "all".
    :returns: Summary dict with chunk count and child flow results.
    """
    logger = get_run_logger()
    start, end = resolve_date_range(date_start, date_end)
    chunks = list(monthly_chunks(start, end, chunk_months=chunk_months))
    selected_flows = _get_ingest_flows(dataset)
    logger.info(
        "Backfill start: start=%s end=%s chunk_months=%s chunks=%s datasets=%s",
        start,
        end,
        chunk_months,
        len(chunks),
        [name for name, _flow in selected_flows],
    )

    submitted: list[tuple[str, str, str, asyncio.Task[int]]] = []
    for chunk_start, chunk_end in chunks:
        for dataset_name, ingest_flow in selected_flows:
            logger.info(
                "Starting child ingest flow: dataset=%s start=%s end=%s",
                dataset_name,
                chunk_start,
                chunk_end,
            )
            child_task = asyncio.create_task(
                ingest_flow(
                    date_start=chunk_start,
                    date_end=chunk_end,
                )
            )
            submitted.append((dataset_name, chunk_start, chunk_end, child_task))

    runs: list[dict[str, Any]] = []
    for dataset_name, chunk_start, chunk_end, child_task in submitted:
        rows_upserted = await child_task
        runs.append(
            {
                "dataset": dataset_name,
                "date_start": chunk_start,
                "date_end": chunk_end,
                "rows_upserted": rows_upserted,
            }
        )

    logger.info("Backfill complete: child_runs=%s", len(runs))
    return {"chunks": len(chunks), "total_runs": len(runs), "runs": runs}
