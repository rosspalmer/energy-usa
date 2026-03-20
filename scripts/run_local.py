#!/usr/bin/env python
"""Run EIA ingest flows directly without the Prefect server.

Use this for debugging and building historical datasets. Full Python
tracebacks appear in the terminal — no Prefect UI required.

Usage:
    uv run python scripts/run_local.py --dataset retail_sales --start 2020-01 --end 2020-06
    uv run python scripts/run_local.py --dataset all --start 2015-01 --end 2024-12

The same flows run as in production, just without Prefect tracking state remotely.
Requires EIA_API_KEY and DATABASE_URL (INGEST) in your .env or environment.
"""

import argparse
import asyncio
import sys

DATASETS = [
    "retail_sales",
    "electric_power_operational",
    "state_source_disposition",
    "state_summary",
    "all",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run EIA ingest flows locally (no Prefect server needed).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python scripts/run_local.py --dataset retail_sales --start 2020-01 --end 2020-06
  uv run python scripts/run_local.py --dataset all --start 2015-01 --end 2024-12 --chunks 3
        """,
    )
    parser.add_argument(
        "--dataset",
        choices=DATASETS,
        required=True,
        help="Which EIA dataset to ingest ('all' runs all four).",
    )
    parser.add_argument(
        "--start",
        metavar="YYYY-MM",
        default=None,
        help="Start period (inclusive). Defaults to last calendar month.",
    )
    parser.add_argument(
        "--end",
        metavar="YYYY-MM",
        default=None,
        help="End period (inclusive). Defaults to current month.",
    )
    parser.add_argument(
        "--chunks",
        type=int,
        default=1,
        metavar="N",
        help="Split the date range into chunks of N months (default: 1). "
             "Useful for long backfills to limit memory usage per run.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    # Import here so errors (missing .env, bad deps) surface clearly
    from energy_usa.flows.backfill_eia import backfill_eia

    print(f"Running local ingest: dataset={args.dataset} start={args.start or 'default'} end={args.end or 'default'} chunks={args.chunks}")
    print("(Prefect will log to stdout; state is not tracked remotely)\n")

    result = await backfill_eia(
        date_start=args.start,
        date_end=args.end,
        chunk_months=args.chunks,
        dataset=args.dataset,
    )

    print(f"\nDone. Chunks run: {result['chunks']}, Child runs: {result['total_runs']}")
    for run in result["runs"]:
        print(f"  {run['dataset']} {run['date_start']}→{run['date_end']}: {run['rows_upserted']} rows")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)
