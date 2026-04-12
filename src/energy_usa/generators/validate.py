"""Code generator: render ``audit_rules.sql`` from a :class:`ValidateSpec`.

This module is the orchestrator for the validation rule generation step.
It reads a :class:`~energy_usa.generators.models_validate.ValidateSpec`,
applies the ``audit_rules.sql.j2`` Jinja2 template, and writes the output
file into the appropriate location under ``output_dir``.

Typical usage::

    from pathlib import Path
    from energy_usa.generators.parse_validate import parse_validate_spec_file
    from energy_usa.generators.validate import generate_validate

    spec = parse_validate_spec_file(Path("specs/validate/eia.md"))
    paths = generate_validate(spec)
    print(paths)  # [PosixPath('docker/postgres/init/ingest/eia/audit_rules.sql')]

Output layout (relative to ``output_dir``)::

    docker/postgres/init/ingest/<source>/audit_rules.sql
"""

from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from energy_usa.generators.models_validate import ValidateSpec

# Directory where the Jinja2 templates live (same dir used by ingest.py).
_TEMPLATES_DIR = Path(__file__).parent / "templates"

# Output sub-path relative to repo root
_SQL_SUBPATH = "docker/postgres/init/ingest/{source}/audit_rules.sql"


def _make_jinja_env() -> Environment:
    """Build the Jinja2 environment for the audit_rules template.

    Registers one extra filter:

    ``tojson``
        Converts a Python object (typically a list) to a JSON string
        suitable for embedding in SQL literals, e.g.
        ``["stateid"]`` → ``'["stateid"]'``.

    :returns: A configured :class:`~jinja2.Environment` with
        :class:`~jinja2.StrictUndefined` so typos in template variables
        fail loudly during development.
    """
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )

    def tojson(value: object) -> str:
        """Serialise a Python value to a compact JSON string.

        :param value: Any JSON-serialisable Python object.
        :returns: Compact JSON string, e.g. ``'["stateid"]'``.
        """
        return json.dumps(value, separators=(",", ":"))

    env.filters["tojson"] = tojson
    return env


def generate_validate(
    spec: ValidateSpec,
    output_dir: Path | None = None,
) -> list[Path]:
    """Render ``audit_rules.sql`` for the given :class:`ValidateSpec`.

    Generates one SQL file per source containing all ``INSERT`` statements
    for ``quality.audit_rules``.  The file is written to::

        <output_dir>/docker/postgres/init/ingest/<source>/audit_rules.sql

    All parent directories are created automatically.  An existing file is
    overwritten without warning.

    :param spec: A fully parsed :class:`ValidateSpec`.
    :param output_dir: Root directory for output files.  Defaults to the
        repository root (four parent levels above this source file).
    :returns: A list containing the single :class:`~pathlib.Path` written.
    """
    if output_dir is None:
        # Default: repo root = 4 levels up from this file
        # .../src/energy_usa/generators/validate.py → repo root
        output_dir = Path(__file__).parent.parent.parent.parent.parent

    env = _make_jinja_env()
    tmpl = env.get_template("audit_rules.sql.j2")

    dest = output_dir / _SQL_SUBPATH.format(source=spec.source)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(tmpl.render(spec=spec), encoding="utf-8")

    return [dest]
