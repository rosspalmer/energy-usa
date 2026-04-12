"""Dataclasses for parsed validation specs.

These models are the bridge between the markdown parser
(:mod:`energy_usa.generators.parse_validate`) and the Jinja2 template that
generates ``docker/postgres/init/ingest/<source>/audit_rules.sql``.

Design notes
------------
- Plain :mod:`dataclasses` — no Pydantic overhead; templates only need
  attribute access.
- ``field(default_factory=...)`` prevents the classic shared-list bug for
  mutable defaults.
- The top-level :class:`ValidateSpec` mirrors :class:`SourceSpec` in
  :mod:`energy_usa.generators.models` but carries validation-specific
  information rather than ingest metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NullToleranceSpec:
    """Null-rate tolerance for one column.

    :param column: Postgres column name, e.g. ``"revenue"``.
    :param max_null_pct: Maximum acceptable percentage of NULL values, e.g.
        ``5.0`` means at most 5 % of rows may be NULL.
    """

    column: str
    max_null_pct: float


@dataclass
class DatasetValidationSpec:
    """Validation specification for one EIA dataset table.

    Each field maps to one or more rows that will be inserted into
    ``quality.audit_rules`` by the generated SQL.

    :param name: Dataset name matching the Postgres table, e.g.
        ``"retail_sales"`` (table ``eia.retail_sales``).
    :param date_range_start: Earliest expected period as ``"YYYY-MM"``, e.g.
        ``"2001-01"``.  Informational only — not currently used to generate
        a SQL check.
    :param null_tolerances: One :class:`NullToleranceSpec` per column that
        should have a ``null_rate`` audit rule.
    :param expected_row_count: Raw human-readable string from the spec, e.g.
        ``"~50 rows/month"``.  Stored for documentation; a ``row_count``
        check rule is generated separately when ``min_per_month`` /
        ``max_per_month`` can be parsed.
    :param completeness_dimensions: Column names used as categorical
        dimensions for the completeness check, e.g. ``["stateid"]``.
    :param completeness_frequency: Expected granularity, e.g. ``"monthly"``
        or ``"annual"``.
    :param staleness_months: Maximum acceptable age of the most recent period
        in months.  ``0`` means no staleness check is generated.
    :param range_checks: Free-form list of range check dicts, each expected
        to contain at least ``column``, ``min``, and ``max`` keys.
    """

    name: str
    date_range_start: str
    null_tolerances: list[NullToleranceSpec] = field(default_factory=list)
    expected_row_count: str = ""
    completeness_dimensions: list[str] = field(default_factory=list)
    completeness_frequency: str = "monthly"
    staleness_months: int = 3
    range_checks: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ValidateSpec:
    """Top-level container for all dataset validation specs in one source.

    A single :class:`ValidateSpec` corresponds to one markdown file, e.g.
    ``specs/validate/eia.md``.  The template generator iterates over
    ``datasets`` to produce all ``INSERT`` statements for ``audit_rules``.

    :param source: Lowercase source identifier, e.g. ``"eia"``.
    :param datasets: All dataset validation specs parsed from the file, in
        document order.
    """

    source: str
    datasets: list[DatasetValidationSpec]

    def get_dataset(self, name: str) -> DatasetValidationSpec | None:
        """Look up a dataset spec by its name.

        :param name: The :attr:`DatasetValidationSpec.name` to search for.
        :returns: The matching spec, or ``None`` if not found.
        """
        for ds in self.datasets:
            if ds.name == name:
                return ds
        return None
