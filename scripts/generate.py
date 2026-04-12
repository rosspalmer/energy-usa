#!/usr/bin/env -S uv run python
# scripts/generate.py
"""CLI for running code generators from markdown specs.

Usage:
    uv run python scripts/generate.py ingest --source eia
    uv run python scripts/generate.py ingest --source eia --dataset retail_sales
"""
import argparse
import sys
from pathlib import Path

from energy_usa.generators.parse_spec import parse_spec
from energy_usa.generators.ingest import generate_ingest


def cmd_ingest(args: argparse.Namespace) -> None:
    spec_path = Path("specs/ingest") / f"{args.source}.md"
    if not spec_path.exists():
        print(f"ERROR: Spec file not found: {spec_path}")
        sys.exit(1)
    spec = parse_spec(spec_path)
    datasets = [args.dataset] if args.dataset else None
    generated = generate_ingest(spec, datasets=datasets)
    for path in generated:
        print(f"  Generated: {path}")
    print(f"\n{len(generated)} files generated from specs/ingest/{args.source}.md")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate code from markdown specs")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest_parser = sub.add_parser("ingest", help="Generate ingest code")
    ingest_parser.add_argument("--source", required=True, help="Source name (e.g. eia)")
    ingest_parser.add_argument("--dataset", help="Single dataset name (optional)")

    args = parser.parse_args()
    if args.command == "ingest":
        cmd_ingest(args)


if __name__ == "__main__":
    main()
