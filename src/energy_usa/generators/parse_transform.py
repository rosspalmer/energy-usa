"""Markdown parser for transform spec files.

Converts a ``specs/transform/<domain>.md`` file into a
:class:`~energy_usa.generators.models_transform.TransformSpec` ready for
consumption by code-generation templates.

Supported spec format
---------------------
::

    # Electricity Domain Model

    ## electricity.generation_mix
    Combines generation data by fuel type with emissions data to show
    the environmental profile of each state's electricity generation.

    - **Source tables**: eia.state_source_disposition, eia.co2_emissions
    - **Grain**: state, period
    - **Join logic**: Match on stateid + period
    - **Output columns**:
      | Column | Source | Logic | Type |
      |--------|--------|-------|------|
      | state  | eia.state_source_disposition.stateid | direct | TEXT |
    - **Unique key**: (state, period)

Key parsing rules
-----------------
- Domain name: first word of the H1 heading, lowercased.
  e.g. ``# Electricity Domain Model`` → ``"electricity"``.
- Each ``## schema.table_name`` heading starts a table section; everything
  until the next ``##`` or EOF belongs to that table.
- Lines between the ``##`` heading and the first ``**`` bullet are collected
  as the description (stripped).
- ``**Source tables**``: comma-separated list of fully-qualified table names.
- ``**Grain**``: comma-separated list of dimension names.
- ``**Join logic**``: free text after the colon.
- ``**Output columns**``: triggers markdown table parsing; each data row
  contributes one :class:`TransformColumnSpec`.  Columns: Column, Source,
  Logic, Type (case-insensitive header match).
- ``**Unique key**``: parenthesized, comma-separated column names; parens are
  stripped before splitting.
"""

from __future__ import annotations

import re
from pathlib import Path

from energy_usa.generators.models_transform import (
    TransformColumnSpec,
    TransformSpec,
    TransformTableSpec,
)

# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

# Matches a bold label at the start of a list item:
# "- **Label**: value"  or  "  - **Label**:"
_BOLD_LABEL_RE = re.compile(r"\*\*([^*]+)\*\*\s*:?\s*(.*)")


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def parse_transform_spec(text: str) -> TransformSpec:
    """Parse a transform spec markdown string and return a :class:`TransformSpec`.

    :param text: Full contents of a ``specs/transform/*.md`` file.
    :returns: A fully populated :class:`TransformSpec`.
    :raises ValueError: If no H1 heading is found in the text.

    Example::

        from pathlib import Path
        from energy_usa.generators.parse_transform import parse_transform_spec

        spec = parse_transform_spec(Path("specs/transform/electricity.md").read_text())
        print(spec.domain)           # "electricity"
        print(len(spec.tables))      # 2
    """
    lines = text.splitlines()
    domain = _parse_domain_name(lines)
    tables = _parse_table_sections(lines)
    return TransformSpec(domain=domain, tables=tables)


def parse_transform_spec_file(path: Path) -> TransformSpec:
    """Parse a transform spec markdown file.

    A thin wrapper around :func:`parse_transform_spec` that reads the file
    for you.

    :param path: Absolute or relative path to a ``.md`` transform spec file.
    :returns: A fully populated :class:`TransformSpec`.
    :raises FileNotFoundError: If ``path`` does not exist.
    :raises ValueError: If the file has no H1 heading.
    """
    return parse_transform_spec(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_domain_name(lines: list[str]) -> str:
    """Extract the domain name from the H1 heading.

    Takes the first word of the heading and lowercases it.  For example::

        # Electricity Domain Model   →   "electricity"
        # Fossil Fuels               →   "fossil"

    :param lines: All lines of the spec file.
    :returns: Lowercase domain identifier.
    :raises ValueError: If no H1 heading is found.
    """
    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            heading = line[2:].strip()
            return heading.split()[0].lower() if heading.split() else heading.lower()
    raise ValueError("No H1 heading found in transform spec")


def _parse_table_sections(lines: list[str]) -> list[TransformTableSpec]:
    """Parse all ``## schema.table_name`` sections.

    :param lines: All lines of the spec file.
    :returns: Ordered list of :class:`TransformTableSpec` objects.
    """
    tables: list[TransformTableSpec] = []
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip()

        # H1 headings are the file title — skip
        if stripped.startswith("# ") and not stripped.startswith("## "):
            continue

        if stripped.startswith("## "):
            # Flush the previous section
            if current_heading is not None:
                tables.append(_parse_one_table(current_heading, current_lines))
            current_heading = stripped[3:].strip()
            current_lines = []
        elif current_heading is not None:
            current_lines.append(line)

    # Flush the last section
    if current_heading is not None:
        tables.append(_parse_one_table(current_heading, current_lines))

    return tables


def _parse_one_table(heading: str, lines: list[str]) -> TransformTableSpec:
    """Parse the body lines of a single ``## schema.table_name`` block.

    The heading may be ``"electricity.generation_mix"``; the table name
    is the part after the dot (``"generation_mix"``).  If there is no dot
    the full heading is used as the table name.

    :param heading: Raw text after ``## ``, e.g. ``"electricity.generation_mix"``.
    :param lines: Lines following the heading up to the next heading or EOF.
    :returns: A populated :class:`TransformTableSpec`.
    """
    # Derive the short table name from the heading
    table_name = heading.split(".", 1)[-1].strip() if "." in heading else heading.strip()

    description_lines: list[str] = []
    source_tables: list[str] = []
    grain: list[str] = []
    join_logic = ""
    columns: list[TransformColumnSpec] = []
    unique_key: tuple[str, ...] = ()

    # State flags
    in_columns_table = False
    col_header_seen = False
    col_separator_seen = False
    description_done = False

    for line in lines:
        stripped = line.strip()

        # Blank lines before the first bold bullet are part of the description
        # area; we stop collecting description once we see the first bullet.
        if not description_done and not stripped.startswith("- **") and not stripped.startswith("| "):
            if stripped:  # non-blank → description text
                description_lines.append(stripped)
            continue

        # Detect bold-label list items
        m = _BOLD_LABEL_RE.search(stripped)
        if m and stripped.startswith("- **"):
            description_done = True
            in_columns_table = False  # reset table mode unless label is Output columns
            col_header_seen = False
            col_separator_seen = False

            label = m.group(1).strip().lower()
            value = m.group(2).strip()

            if label == "source tables":
                source_tables = [t.strip() for t in value.split(",") if t.strip()]

            elif label == "grain":
                grain = [g.strip() for g in value.split(",") if g.strip()]

            elif label == "join logic":
                join_logic = value

            elif label == "output columns":
                in_columns_table = True  # table rows follow on subsequent lines

            elif label == "unique key":
                # Strip surrounding parens, then split on commas
                clean = value.strip().strip("()")
                unique_key = tuple(k.strip() for k in clean.split(",") if k.strip())

            continue

        # Parse output-columns table rows
        if in_columns_table and stripped.startswith("|"):
            cells = _split_table_row(stripped)

            if not col_header_seen:
                col_header_seen = True
                continue  # skip header row

            if not col_separator_seen:
                # Separator row: cells are like "------" or ":---:"
                if all(re.match(r"^[-:]+$", c) for c in cells if c):
                    col_separator_seen = True
                    continue

            # Data row: | Column | Source | Logic | Type |
            if len(cells) >= 4 and cells[0]:
                columns.append(
                    TransformColumnSpec(
                        name=cells[0],
                        source=cells[1],
                        logic=cells[2],
                        pg_type=cells[3] if cells[3] else "NUMERIC",
                    )
                )
            continue

        # A non-table line inside a column table ends the table block
        if in_columns_table and not stripped.startswith("|"):
            in_columns_table = False

    description = " ".join(description_lines).strip()

    return TransformTableSpec(
        name=table_name,
        description=description,
        source_tables=source_tables,
        grain=grain,
        join_logic=join_logic,
        columns=columns,
        unique_key=unique_key,
    )


def _split_table_row(row: str) -> list[str]:
    """Split a ``|``-delimited Markdown table row into stripped cell strings.

    :param row: A single Markdown table row, e.g.
        ``"| state | eia.retail_sales.stateid | direct | TEXT |"``.
    :returns: List of stripped cell strings (empty edge cells omitted).
    """
    return [c.strip() for c in row.strip("|").split("|")]
