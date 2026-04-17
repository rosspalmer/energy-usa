"""Prefect flow to backfill EIA datasets in cadence-aware chunks, in parallel.

Dynamically discovers ingest flows by source name. Each per-dataset flow exposes
its publication cadence as a ``CADENCE`` module constant (annual, quarterly,
monthly, daily). The parent ``backfill_eia`` flow:

* picks a chunk size for each dataset based on its cadence (annual = 12 months,
  quarterly = 3, monthly/daily = 1) so we don't make N redundant requests for
  the same yearly record,
* fans out chunks across datasets concurrently using ``asyncio.gather`` with a
  semaphore so we stay within EIA's rate limits, and
* survives per-chunk failures (e.g. trailing months with no published data
  yet) — those are logged and counted but do not abort the whole job.
"""

import asyncio
import importlib
import pkgutil
from itertools import zip_longest
from typing import Awaitable, Callable, Literal, NamedTuple

from prefect import flow
from prefect.logging import get_run_logger

from energy_usa.flows.date_range import monthly_chunks, resolve_date_range

IngestFlow = Callable[..., Awaitable[int]]

# Maximum number of dataset chunks executed concurrently against the EIA API.
# Each subflow internally fans out up to ``EIA_MAX_CONCURRENT_REQUESTS`` page
# requests (default 4), so peak concurrency is roughly this number times that
# value. EIA returns HTTP 429 well below its nominal 5000 req/hr quota when
# bursts are too tight, so we keep this small. Bump only if you've tuned
# EIA_PAGE_DELAY_SECONDS up at the same time.
MAX_PARALLEL_CHUNKS = 3

# How many months of data each chunk covers, by cadence. Annual data is one
# row per year so a 12-month chunk = 1 record; quarterly = 3 months = 1 record;
# monthly/daily stay at 1-month chunks (daily data still fits comfortably in
# a per-month request).
CHUNK_MONTHS_BY_CADENCE: dict[str, int] = {
    "annual": 12,
    "quarterly": 3,
    "monthly": 1,
    "daily": 1,
}


class DatasetTarget(NamedTuple):
    """One discovered dataset: its name, cadence, and async flow function."""

    name: str
    cadence: str
    flow: IngestFlow


def get_flow_registry(source: str) -> dict[str, DatasetTarget]:
    """Discover all ingest flows for a source by importing its package.

    Looks for functions named ``ingest_<source>_<dataset>`` in each module
    under ``energy_usa.flows.ingest.<source>``. The cadence is read from the
    module's ``CADENCE`` constant (defaults to ``"monthly"`` if missing).

    :param source: Source name (e.g. 'eia').
    :returns: Dict mapping dataset name to :class:`DatasetTarget`.
    """
    registry: dict[str, DatasetTarget] = {}
    package_name = f"energy_usa.flows.ingest.{source}"
    try:
        package = importlib.import_module(package_name)
    except ModuleNotFoundError:
        return registry

    prefix = f"ingest_{source}_"
    for _importer, module_name, _is_pkg in pkgutil.iter_modules(package.__path__):
        mod = importlib.import_module(f"{package_name}.{module_name}")
        cadence = getattr(mod, "CADENCE", "monthly")
        for attr_name in dir(mod):
            if attr_name.startswith(prefix):
                dataset_name = attr_name[len(prefix):]
                fn = getattr(mod, attr_name)
                if callable(fn):
                    registry[dataset_name] = DatasetTarget(dataset_name, cadence, fn)
    return registry


# Discover EIA datasets at import time for the Literal type
_EIA_REGISTRY = get_flow_registry("eia")
DatasetName = Literal[tuple(["all"] + sorted(_EIA_REGISTRY.keys()))]  # type: ignore[valid-type]


async def _run_chunk(
    sem: asyncio.Semaphore,
    target: DatasetTarget,
    chunk_start: str,
    chunk_end: str,
) -> tuple[DatasetTarget, str, str, Exception | None]:
    """Run one (dataset, chunk) under a concurrency semaphore.

    Returns a tuple suitable for accumulating into the failure list. The error
    slot is ``None`` on success, otherwise the caught exception.
    """
    logger = get_run_logger()
    async with sem:
        logger.info(
            "Starting %s [%s]: %s to %s",
            target.name, target.cadence, chunk_start, chunk_end,
        )
        try:
            await target.flow(date_start=chunk_start, date_end=chunk_end)
            return target, chunk_start, chunk_end, None
        except Exception as exc:  # noqa: BLE001 — we log and continue
            logger.warning(
                "Chunk failed: %s %s→%s — %s",
                target.name, chunk_start, chunk_end, exc,
            )
            return target, chunk_start, chunk_end, exc


@flow(
    name="backfill-eia",
    # Prefect interpolates {param} templates against the runtime params, so this
    # produces e.g. "2020-01 - 2026-04: backfill" in the UI.
    flow_run_name="{date_start} - {date_end}: backfill",
    timeout_seconds=86400,
)
async def backfill_eia(
    date_start: str | None = None,
    date_end: str | None = None,
    dataset: DatasetName = "retail_sales",
) -> None:
    """Backfill one or all EIA datasets over a date range, in cadence-aware chunks.

    Each dataset's chunk size is derived from its publication cadence (so
    annual datasets run a single chunk per year, etc.). Chunks fan out
    across datasets in parallel with a semaphore cap of
    :data:`MAX_PARALLEL_CHUNKS`.

    :param date_start: Start period (YYYY-MM). Defaults to last month.
    :param date_end: End period (YYYY-MM). Defaults to current month.
    :param dataset: Dataset key or 'all'.
    """
    logger = get_run_logger()
    registry = get_flow_registry("eia")

    if dataset == "all":
        targets = list(registry.values())
    else:
        if dataset not in registry:
            raise ValueError(
                f"Unknown dataset '{dataset}'. Available: {sorted(registry.keys())}"
            )
        targets = [registry[dataset]]

    start, end = resolve_date_range(date_start, date_end)

    # Build per-dataset chunk lists, then *interleave* them so consecutive
    # work items come from different datasets. Without this the work list is
    # dataset-major (all of aeo's chunks, then all of biomass_capacity's, …),
    # so the semaphore fills with N chunks of the *same* big slow dataset
    # competing for the same EIA endpoint and API quota — nothing else makes
    # progress until aeo finishes. Round-robin keeps the first N concurrent
    # slots spread across N different datasets.
    per_dataset_chunks: list[list[tuple[DatasetTarget, str, str]]] = []
    for target in targets:
        size = CHUNK_MONTHS_BY_CADENCE.get(target.cadence, 1)
        per_dataset_chunks.append([
            (target, cs, ce) for (cs, ce) in monthly_chunks(start, end, size)
        ])
    work: list[tuple[DatasetTarget, str, str]] = []
    for column in zip_longest(*per_dataset_chunks):
        for item in column:
            if item is not None:
                work.append(item)

    logger.info(
        "Backfill: %d dataset(s), %d chunk(s) total, range %s to %s, "
        "parallelism=%d",
        len(targets), len(work), start, end, MAX_PARALLEL_CHUNKS,
    )

    sem = asyncio.Semaphore(MAX_PARALLEL_CHUNKS)
    results = await asyncio.gather(
        *[_run_chunk(sem, t, cs, ce) for (t, cs, ce) in work],
        return_exceptions=False,
    )

    failures = [(t.name, cs, ce, err) for (t, cs, ce, err) in results if err is not None]
    succeeded = len(results) - len(failures)
    logger.info(
        "Backfill complete: %d/%d chunks succeeded, %d failed",
        succeeded, len(results), len(failures),
    )
    if failures:
        logger.warning("Failed chunks (first 20):")
        for ds_name, cs, ce, err in failures[:20]:
            logger.warning("  %s %s→%s: %s", ds_name, cs, ce, err)
