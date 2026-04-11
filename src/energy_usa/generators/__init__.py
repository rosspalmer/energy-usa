"""Code generation utilities for the energy_usa data platform.

This sub-package transforms declarative markdown spec files into production
Python source code — Prefect flows, Postgres DDL, and upsert modules — so
that adding a new EIA dataset requires only a single spec file, not manual
edits to multiple source files.

Typical usage::

    from energy_usa.generators.parse_spec import parse_spec
    from energy_usa.generators.models import SourceSpec

    source: SourceSpec = parse_spec(Path("specs/ingest/eia.md"))
"""
