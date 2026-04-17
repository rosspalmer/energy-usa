"""Code generator: render SQL DDL, db upsert module, and Prefect flow from a SourceSpec.

This module is the orchestrator for Tasks 4–5 of the generator pipeline.
It reads a :class:`~energy_usa.generators.models.SourceSpec`, applies three
Jinja2 templates, and writes the output files into the appropriate locations
under ``output_dir``.

Typical usage::

    from pathlib import Path
    from energy_usa.generators.parse_spec import parse_spec
    from energy_usa.generators.ingest import generate_ingest

    spec = parse_spec(Path("specs/ingest/eia.md"))
    paths = generate_ingest(spec, output_dir=Path("generated"))

Output layout (relative to ``output_dir``)::

    docker/postgres/init/ingest/eia/<name>.sql
    src/energy_usa/db/ingest/eia/<name>.py
    src/energy_usa/flows/ingest/eia/<name>.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from energy_usa.generators.models import DatasetSpec, SourceSpec

# Directory where the three ``.j2`` templates live.
_TEMPLATES_DIR = Path(__file__).parent / "templates"

# Sub-paths (relative to output_dir) for each generated file type.
_SQL_SUBPATH = "docker/postgres/init/ingest/eia/{name}.sql"
_DB_SUBPATH = "src/energy_usa/db/ingest/eia/{name}.py"
_FLOW_SUBPATH = "src/energy_usa/flows/ingest/eia/{name}.py"


def _make_jinja_env() -> Environment:
    """Build and return the Jinja2 :class:`~jinja2.Environment` for ingest templates.

    Two custom filters are registered:

    ``fmt_params``
        Converts a list of column names into a comma-separated string of
        ``%(name)s`` psycopg parameter placeholders.  Used in the VALUES clause
        of the INSERT statement.

        Example: ``["period", "stateid"]`` → ``"%(period)s, %(stateid)s"``

    ``fmt_get``
        Converts a single API field name into a ``r.get("field")`` expression,
        ready to be joined with ``" or "`` for alias fallback chains.

        Example: ``"stateId"`` → ``r.get("stateId")``

    :returns: A configured :class:`~jinja2.Environment` with
        ``StrictUndefined`` so template typos fail loudly.
    """
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )

    def fmt_params(names: list[str]) -> str:
        """Render a list of column names as psycopg ``%(name)s`` placeholders.

        :param names: Column name strings.
        :returns: Comma-separated placeholder string.
        """
        return ", ".join(f"%({n})s" for n in names)

    def fmt_get(field: str) -> str:
        """Render a single API field name as a ``r.get(...)`` call.

        :param field: API field name (may contain hyphens or camelCase).
        :returns: Python expression string.
        """
        return f'r.get("{field}")'

    def elec_subpath(api_path: str) -> str:
        """Extract the subpath for ``get_electricity(subpath=...)`` calls.

        The EIA client prepends ``electricity/`` automatically.  Given an
        ``api_path`` like ``/electricity/retail-sales``, this filter returns
        ``retail-sales`` (without the ``electricity/`` prefix or leading slash).

        :param api_path: Full API path from the spec (e.g. ``/electricity/retail-sales``).
        :returns: Subpath without the ``electricity/`` prefix.
        """
        path = api_path.lstrip("/")
        # Strip the "electricity/" or "electricity" prefix if present
        if path.startswith("electricity/"):
            path = path[len("electricity/"):]
        elif path == "electricity":
            path = ""
        return path

    env.filters["fmt_params"] = fmt_params
    env.filters["fmt_get"] = fmt_get
    env.filters["elec_subpath"] = elec_subpath

    return env


def generate_ingest(
    spec: SourceSpec,
    output_dir: Path | None = None,
    datasets: Sequence[str] | None = None,
) -> list[Path]:
    """Generate SQL DDL, db upsert module, and Prefect flow files for a SourceSpec.

    For each dataset in ``spec`` (or the subset named by ``datasets``), three
    files are written:

    - ``docker/postgres/init/ingest/eia/<name>.sql`` — CREATE TABLE DDL
    - ``src/energy_usa/db/ingest/eia/<name>.py`` — psycopg upsert function
    - ``src/energy_usa/flows/ingest/eia/<name>.py`` — Prefect flow

    All parent directories are created automatically.  Existing files are
    overwritten without warning.

    :param spec: A fully parsed :class:`~energy_usa.generators.models.SourceSpec`.
    :param output_dir: Root directory to write generated files.  Defaults to
        the repository root (two levels above this file's ``src/`` tree).
    :param datasets: Optional list of dataset names to generate.  When
        ``None`` (the default), all datasets in ``spec`` are generated.
    :returns: List of :class:`~pathlib.Path` objects for every file written,
        in the order SQL → db → flow, dataset by dataset.
    """
    if output_dir is None:
        # Default: repo root = 4 levels up from this file
        # .../src/energy_usa/generators/ingest.py → repo root
        output_dir = Path(__file__).parent.parent.parent.parent

    env = _make_jinja_env()
    sql_tmpl = env.get_template("schema.sql.j2")
    db_tmpl = env.get_template("db_module.py.j2")
    flow_tmpl = env.get_template("flow_module.py.j2")

    target_names: set[str] | None = set(datasets) if datasets is not None else None

    written: list[Path] = []

    for dataset in spec.datasets:
        if target_names is not None and dataset.name not in target_names:
            continue

        written.extend(_render_dataset(dataset, output_dir, sql_tmpl, db_tmpl, flow_tmpl))

    return written


# ── Internal helpers ──────────────────────────────────────────────────────────


def _render_dataset(
    dataset: DatasetSpec,
    output_dir: Path,
    sql_tmpl,
    db_tmpl,
    flow_tmpl,
) -> list[Path]:
    """Render and write the three output files for a single dataset.

    :param dataset: Dataset specification to render.
    :param output_dir: Root directory for all output files.
    :param sql_tmpl: Compiled Jinja2 template for SQL DDL.
    :param db_tmpl: Compiled Jinja2 template for the db upsert module.
    :param flow_tmpl: Compiled Jinja2 template for the Prefect flow module.
    :returns: List of the three paths that were written.
    """
    ctx = {"dataset": dataset}

    pairs = [
        (_SQL_SUBPATH.format(name=dataset.name), sql_tmpl),
        (_DB_SUBPATH.format(name=dataset.name), db_tmpl),
        (_FLOW_SUBPATH.format(name=dataset.name), flow_tmpl),
    ]

    paths: list[Path] = []
    for subpath, tmpl in pairs:
        dest = output_dir / subpath
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(tmpl.render(**ctx), encoding="utf-8")
        paths.append(dest)

    return paths
