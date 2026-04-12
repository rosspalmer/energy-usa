#!/usr/bin/env -S uv run python
"""CLI for running transform flows.

Usage::

    uv run python scripts/transform.py --domain electricity
    uv run python scripts/transform.py --domain electricity --table retail_by_state

Or via the Makefile::

    make transform DOMAIN=electricity
    make transform DOMAIN=electricity TTABLE=retail_by_state
"""
import argparse
import sys


def main() -> None:
    """Parse arguments and dispatch to the appropriate transform flow.

    :raises SystemExit: With code 1 if the domain is not recognised.
    """
    parser = argparse.ArgumentParser(description="Run transform flows")
    parser.add_argument("--domain", required=True, help="Domain name (e.g. electricity)")
    parser.add_argument("--table", help="Single table (optional)")
    args = parser.parse_args()

    if args.domain == "electricity":
        from energy_usa.flows.transform.electricity import transform_electricity

        tables = [args.table] if args.table else None
        results = transform_electricity(tables=tables)
        print("\nTransform complete:")
        for name, count in results.items():
            print(f"  electricity.{name}: {count} rows")
    else:
        print(f"ERROR: Unknown domain '{args.domain}'")
        sys.exit(1)


if __name__ == "__main__":
    main()
