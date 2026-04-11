"""Prefect flow to backfill datasets in configurable month chunks.

Dynamically discovers ingest flows by source name. The parent flow splits
a date range into chunks and submits one child flow per chunk.
"""

import importlib
import pkgutil
from typing import Any, Awaitable, Callable, Literal

from prefect import flow
from prefect.logging import get_run_logger

from energy_usa.flows.date_range import make_run_name, monthly_chunks, resolve_date_range

IngestFlow = Callable[..., Awaitable[int]]


def get_flow_registry(source: str) -> dict[str, IngestFlow]:
    """Discover all ingest flows for a source by importing its package.

    Looks for functions named ``ingest_<source>_<dataset>`` in each module
    under ``energy_usa.flows.ingest.<source>``.

    :param source: Source name (e.g. 'eia').
    :returns: Dict mapping dataset name to flow function.
    """
    registry: dict[str, IngestFlow] = {}
    package_name = f"energy_usa.flows.ingest.{source}"
    try:
        package = importlib.import_module(package_name)
    except ModuleNotFoundError:
        return registry

    prefix = f"ingest_{source}_"
    for _importer, module_name, _is_pkg in pkgutil.iter_modules(package.__path__):
        mod = importlib.import_module(f"{package_name}.{module_name}")
        for attr_name in dir(mod):
            if attr_name.startswith(prefix):
                dataset_name = attr_name[len(prefix):]
                fn = getattr(mod, attr_name)
                if callable(fn):
                    registry[dataset_name] = fn
    return registry


# Discover EIA datasets at import time for the Literal type
_EIA_REGISTRY = get_flow_registry("eia")
DatasetName = Literal[tuple(["all"] + sorted(_EIA_REGISTRY.keys()))]  # type: ignore[valid-type]


def _run_name(**kwargs: Any) -> str:
    ds = kwargs.get("dataset", "all")
    start = kwargs.get("date_start")
    end = kwargs.get("date_end")
    base = make_run_name("monthly", start, end)
    return f"{base} [{ds}]"


@flow(
    name="backfill-eia",
    flow_run_name=_run_name,
    timeout_seconds=86400,
)
async def backfill_eia(
    date_start: str | None = None,
    date_end: str | None = None,
    chunk_months: int = 1,
    dataset: DatasetName = "retail_sales",
) -> None:
    """Backfill one or all EIA datasets over a date range in monthly chunks.

    :param date_start: Start period (YYYY-MM). Defaults to last month.
    :param date_end: End period (YYYY-MM). Defaults to current month.
    :param chunk_months: Months per chunk (default 1).
    :param dataset: Dataset key or 'all'.
    """
    logger = get_run_logger()
    registry = get_flow_registry("eia")

    if dataset == "all":
        targets = list(registry.items())
    else:
        if dataset not in registry:
            raise ValueError(f"Unknown dataset '{dataset}'. Available: {sorted(registry.keys())}")
        targets = [(dataset, registry[dataset])]

    start, end = resolve_date_range(date_start, date_end)
    chunks = list(monthly_chunks(start, end, chunk_months))
    logger.info(
        "Backfill: %d dataset(s), %d chunk(s), range %s to %s",
        len(targets), len(chunks), start, end,
    )

    for ds_name, ds_flow in targets:
        for chunk_start, chunk_end in chunks:
            logger.info("Running %s: %s to %s", ds_name, chunk_start, chunk_end)
            await ds_flow(date_start=chunk_start, date_end=chunk_end)
