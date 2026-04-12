"""Dataclasses for parsed transform specs.

These models are the bridge between the markdown parser
(:mod:`energy_usa.generators.parse_transform`) and the downstream
code-generation step that will produce Prefect flows, SQL DDL, and
transform DB modules.

Design notes
------------
- Plain :mod:`dataclasses` — no Pydantic overhead; keeps the generator
  layer dependency-free so it can be used in CI and dev tooling without
  requiring the full project runtime.
- ``field(default_factory=...)`` prevents the classic shared-list bug for
  mutable defaults on list fields.
- The three-tier hierarchy mirrors the spec markdown structure:
  ``TransformSpec`` (one file) → ``TransformTableSpec`` (one ``##`` section)
  → ``TransformColumnSpec`` (one output-column table row).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TransformColumnSpec:
    """A single output column in a transform table.

    :param name: Postgres column name in the output table,
        e.g. ``"total_sales"``.
    :param source: Dot-separated source reference such as
        ``"eia.retail_sales.sales"``, or the literal string ``"derived"``
        when the column is computed from other output columns.
    :param logic: Human-readable derivation rule, e.g. ``"direct"``,
        ``"sum by state+period"``, or ``"total_revenue / total_sales"``.
    :param pg_type: Postgres column type string, e.g. ``"NUMERIC"``,
        ``"TEXT"``, or ``"DATE"``.  Defaults to ``"NUMERIC"``.
    """

    name: str
    source: str           # "eia.retail_sales.stateid" or "derived"
    logic: str            # "direct", "sum by state+period", "col_a / col_b"
    pg_type: str = "NUMERIC"


@dataclass
class TransformTableSpec:
    """A single output table in a transform domain.

    Captures everything needed to generate a Prefect task, Postgres DDL,
    and a ``db/transform/<domain>/`` write module.

    :param name: Short table name without schema prefix,
        e.g. ``"generation_mix"`` (full name: ``electricity.generation_mix``).
    :param description: Plain-English purpose of the table, suitable for
        inline SQL comments and documentation.
    :param source_tables: Fully-qualified source tables read by this
        transform, e.g. ``["eia.state_source_disposition", "eia.co2_emissions"]``.
    :param grain: Dimension names that define one row, e.g.
        ``["state", "period"]``.
    :param join_logic: Free-text description of how sources are combined.
    :param columns: Ordered list of :class:`TransformColumnSpec` objects
        that make up the output table.
    :param unique_key: Column names that form the ``ON CONFLICT`` target,
        e.g. ``("state", "period")``.
    """

    name: str             # "generation_mix"
    description: str
    source_tables: list[str]
    grain: list[str]      # ["state", "period"]
    join_logic: str
    columns: list[TransformColumnSpec]
    unique_key: tuple[str, ...]


@dataclass
class TransformSpec:
    """Top-level container for all transform table specs in one domain.

    A single :class:`TransformSpec` corresponds to one markdown file, e.g.
    ``specs/transform/electricity.md``.  The code generator iterates over
    ``tables`` to produce all output artifacts for the domain.

    :param domain: Lowercase domain identifier, e.g. ``"electricity"``.
    :param tables: All table specs parsed from the file, in document order.
    """

    domain: str           # "electricity"
    tables: list[TransformTableSpec] = field(default_factory=list)

    def get_table(self, name: str) -> TransformTableSpec | None:
        """Look up a table spec by its short name.

        :param name: The :attr:`TransformTableSpec.name` to search for.
        :returns: The matching spec, or ``None`` if not found.

        Example::

            spec.get_table("retail_by_state")
        """
        for t in self.tables:
            if t.name == name:
                return t
        return None
