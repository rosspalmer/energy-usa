"""Markdown spec parser — converts ``.md`` spec files into typed model objects.

The parser is a single-pass line-by-line state machine.  It recognises the
structure used in ``specs/ingest/_template.md`` and produces a
:class:`~energy_usa.generators.models.SourceSpec` ready for consumption by
code-generation templates.

Supported spec sections
-----------------------
``# <Source Name> — <Subtitle>``
    Source name (everything before the ``—`` or ``-``, lowercased).

``## Source``
    Base URL, auth env var, and rate-limit settings.

``## Datasets``
    One or more ``### <dataset_name>`` subsections, each containing:

    - ``**API path**``, ``**API method**``, ``**Frequency**``
    - ``**Unique key**``: ``(col1, col2, ...)``
    - ``**Columns**`` — a Markdown table (header + separator + data rows)
    - ``**Filters**`` — ``Skip rows where field = 'value'``
    - ``**Extra API params**`` — ``key=value, key2=value2``
    - ``**History**`` — ``YYYY-MM``
    - ``**Indexes**`` — ``col1, col2``

Example usage::

    from pathlib import Path
    from energy_usa.generators.parse_spec import parse_spec

    source = parse_spec(Path("specs/ingest/eia.md"))
    print(source.name)           # "eia"
    print(source.datasets[0].name)  # "retail_sales"

Notes
-----
- The parser is intentionally lenient on whitespace and capitalisation in
  bold-label lines so that spec authors don't have to memorise exact spacing.
- Column table rows with fewer than 4 cells are silently skipped (handles
  accidental blank table rows).
- API aliases in the API-field cell are separated by ``;`` and stripped.
"""

from __future__ import annotations

import re
from pathlib import Path

from energy_usa.generators.models import (
    ColumnSpec,
    DatasetSpec,
    FilterSpec,
    SourceSpec,
)

# ── Regex helpers ─────────────────────────────────────────────────────────────

# Matches "4 concurrent requests, 500ms page delay"
_RATE_RE = re.compile(
    r"(\d+)\s+concurrent\s+requests,\s*(\d+(?:\.\d+)?)\s*ms\s+page\s+delay",
    re.IGNORECASE,
)

# Matches "Skip rows where field = 'value'"
_FILTER_RE = re.compile(
    r"where\s+(\w+)\s*=\s*'([^']+)'",
    re.IGNORECASE,
)

# Matches a bold label in a list item: "- **Label**: value"
_BOLD_LABEL_RE = re.compile(
    r"\*\*([^*]+)\*\*\s*:?\s*(.*)",
)

# Matches the unique-key tuple "(col1, col2, col3)"
_KEY_RE = re.compile(r"\(([^)]+)\)")


# ── Public entry point ────────────────────────────────────────────────────────


def parse_spec(path: Path) -> SourceSpec:
    """Parse a markdown spec file and return a :class:`SourceSpec`.

    :param path: Absolute or relative path to a ``.md`` spec file.
    :returns: A fully populated :class:`~energy_usa.generators.models.SourceSpec`.
    :raises ValueError: If the H1 heading or ``## Source`` section is missing.
    :raises FileNotFoundError: If ``path`` does not exist.
    """
    text = path.read_text(encoding="utf-8")
    return parse_spec_text(text)


def parse_spec_text(text: str) -> SourceSpec:
    """Parse a markdown spec string and return a :class:`SourceSpec`.

    This is the main entry point used by tests (where constructing a real
    ``Path`` is inconvenient).  :func:`parse_spec` delegates here after
    reading the file.

    :param text: Full contents of a spec ``.md`` file.
    :returns: A fully populated :class:`~energy_usa.generators.models.SourceSpec`.
    :raises ValueError: If mandatory sections are absent.
    """
    lines = text.splitlines()
    source_name = _parse_source_name(lines)
    source_meta = _parse_source_section(lines)
    datasets = _parse_datasets_section(lines)

    return SourceSpec(
        name=source_name,
        base_url=source_meta["base_url"],
        api_key_env=source_meta["api_key_env"],
        max_concurrent=source_meta["max_concurrent"],
        page_delay=source_meta["page_delay"],
        datasets=datasets,
    )


# ── Section parsers ───────────────────────────────────────────────────────────


def _parse_source_name(lines: list[str]) -> str:
    """Extract the source name from the H1 heading.

    The heading format is::

        # EIA — U.S. Energy Information Administration

    or with an ASCII hyphen::

        # EIA - U.S. Energy Information Administration

    The source name is the text before the first ``—`` or ``-``, stripped and
    lowercased.

    :param lines: All lines of the spec file.
    :returns: Lowercase source identifier, e.g. ``"eia"``.
    :raises ValueError: If no H1 heading is found.
    """
    for line in lines:
        if line.startswith("# "):
            heading = line[2:].strip()
            # Split on em-dash or ASCII hyphen surrounded by spaces
            for sep in ("—", " - "):
                if sep in heading:
                    return heading.split(sep, 1)[0].strip().lower()
            # No separator — use the whole heading
            return heading.lower()
    raise ValueError("No H1 heading found in spec")


def _parse_source_section(lines: list[str]) -> dict:
    """Extract base_url, api_key_env, max_concurrent, page_delay.

    Looks for ``## Source`` then reads bold-labelled list items until the next
    ``##`` section or end of file.

    :param lines: All lines of the spec file.
    :returns: Dict with keys ``base_url``, ``api_key_env``, ``max_concurrent``,
        ``page_delay``.
    :raises ValueError: If ``## Source`` section is not found.
    """
    in_section = False
    result: dict = {
        "base_url": "",
        "api_key_env": "",
        "max_concurrent": 1,
        "page_delay": 0.0,
    }

    for line in lines:
        stripped = line.strip()

        if stripped.lower() == "## source":
            in_section = True
            continue

        if in_section and stripped.startswith("## "):
            break  # next section — stop

        if not in_section:
            continue

        m = _BOLD_LABEL_RE.search(stripped)
        if not m:
            continue

        label = m.group(1).strip().lower()
        value = m.group(2).strip()

        if label == "base url":
            result["base_url"] = value
        elif label == "auth":
            # Extract env var name: "API key via query param `api_key`, env var `EIA_API_KEY`"
            env_match = re.search(r"env\s+var\s+`([^`]+)`", value, re.IGNORECASE)
            if env_match:
                result["api_key_env"] = env_match.group(1)
        elif label == "rate limit":
            rate_m = _RATE_RE.search(value)
            if rate_m:
                result["max_concurrent"] = int(rate_m.group(1))
                result["page_delay"] = int(rate_m.group(2)) / 1000.0

    if not result["base_url"]:
        raise ValueError("## Source section not found or missing Base URL")

    return result


def _parse_datasets_section(lines: list[str]) -> list[DatasetSpec]:
    """Parse all ``### dataset_name`` subsections under ``## Datasets``.

    :param lines: All lines of the spec file.
    :returns: List of :class:`DatasetSpec` objects in document order.
    """
    datasets: list[DatasetSpec] = []
    in_datasets = False
    current_dataset_lines: list[str] = []
    current_name: str | None = None

    for line in lines:
        stripped = line.strip()

        if stripped.lower() == "## datasets":
            in_datasets = True
            continue

        if in_datasets and stripped.startswith("## ") and not stripped.startswith("### "):
            # Left the ## Datasets section
            if current_name and current_dataset_lines:
                datasets.append(_parse_one_dataset(current_name, current_dataset_lines))
            break

        if not in_datasets:
            continue

        if stripped.startswith("### "):
            # Flush previous dataset
            if current_name and current_dataset_lines:
                datasets.append(_parse_one_dataset(current_name, current_dataset_lines))
            current_name = stripped[4:].strip()
            current_dataset_lines = []
        elif current_name is not None:
            current_dataset_lines.append(line)

    # Flush final dataset
    if current_name and current_dataset_lines:
        datasets.append(_parse_one_dataset(current_name, current_dataset_lines))

    return datasets


def _parse_one_dataset(name: str, lines: list[str]) -> DatasetSpec:
    """Parse the lines belonging to a single ``### dataset_name`` block.

    :param name: Dataset name (from the ``###`` heading text).
    :param lines: Lines from directly after the heading up to the next heading.
    :returns: A :class:`DatasetSpec`.
    """
    api_path = ""
    api_method = ""
    frequency = ""
    unique_key: tuple[str, ...] = ()
    columns: list[ColumnSpec] = []
    filters: list[FilterSpec] = []
    history_start = ""
    extra_api_params: dict[str, str] = {}
    indexes: list[str] = []

    # State for multi-line column table
    in_columns = False
    col_header_seen = False
    col_separator_seen = False

    for line in lines:
        stripped = line.strip()

        # ── Detect bold-label lines ──────────────────────────────────────────
        m = _BOLD_LABEL_RE.search(stripped)
        if m and not stripped.startswith("|"):
            label = m.group(1).strip().lower()
            value = m.group(2).strip()

            if label == "api path":
                api_path = value
                in_columns = False
            elif label == "api method":
                api_method = value
                in_columns = False
            elif label == "frequency":
                frequency = value
                in_columns = False
            elif label == "unique key":
                unique_key = _parse_unique_key(value)
                in_columns = False
            elif label == "columns":
                # The table follows on subsequent lines
                in_columns = True
                col_header_seen = False
                col_separator_seen = False
                # value might be empty or have inline table start — handled below
            elif label == "filters":
                in_columns = False
                filter_m = _FILTER_RE.search(value)
                if filter_m:
                    filters.append(
                        FilterSpec(
                            field=filter_m.group(1),
                            operator="=",
                            value=filter_m.group(2),
                        )
                    )
            elif label == "extra api params":
                in_columns = False
                extra_api_params = _parse_extra_params(value)
            elif label == "history":
                in_columns = False
                history_start = value
            elif label == "indexes":
                in_columns = False
                indexes = [s.strip() for s in value.split(",") if s.strip()]
            continue  # bold-label handled

        # ── Column table rows ────────────────────────────────────────────────
        if in_columns and stripped.startswith("|"):
            cells = _split_table_row(stripped)

            if not col_header_seen:
                col_header_seen = True
                continue  # skip header row

            if not col_separator_seen:
                # Separator row looks like "|---|---|...|"
                if all(re.match(r"^[-:]+$", c) for c in cells if c):
                    col_separator_seen = True
                    continue

            # Data row
            col = _parse_column_row(cells)
            if col is not None:
                columns.append(col)
            continue

        # ── Filters on their own line (not inline with label) ────────────────
        if stripped.lower().startswith("skip rows"):
            filter_m = _FILTER_RE.search(stripped)
            if filter_m:
                filters.append(
                    FilterSpec(
                        field=filter_m.group(1),
                        operator="=",
                        value=filter_m.group(2),
                    )
                )

        # Non-table, non-label lines reset the column-table state so stray
        # blank lines between the label and the table don't break parsing.
        # We intentionally do NOT reset in_columns on blank lines because
        # some editors insert a blank line between the label and the table.

    return DatasetSpec(
        name=name,
        api_path=api_path,
        api_method=api_method,
        frequency=frequency,
        unique_key=unique_key,
        columns=columns,
        filters=filters,
        history_start=history_start,
        extra_api_params=extra_api_params,
        indexes=indexes,
    )


# ── Row/cell helpers ──────────────────────────────────────────────────────────


def _split_table_row(row: str) -> list[str]:
    """Split a ``|``-delimited Markdown table row into stripped cell strings.

    Leading and trailing ``|`` characters are removed before splitting, and
    each cell is stripped of surrounding whitespace.

    :param row: A single Markdown table row, e.g.
        ``"| period | period | DATE | yes | |"``.
    :returns: List of cell strings with empty edge cells omitted.
    """
    # Strip leading/trailing pipe then split
    return [c.strip() for c in row.strip("|").split("|")]


def _parse_column_row(cells: list[str]) -> ColumnSpec | None:
    """Build a :class:`ColumnSpec` from a list of table cells.

    Expected cell positions:

    0. Column name (Postgres)
    1. API field(s) — primary name, with optional aliases separated by ``;``
    2. Postgres type
    3. Required flag (``"yes"`` or ``"no"``)
    4. Default value (may be empty string or absent)

    :param cells: Stripped cell strings from :func:`_split_table_row`.
    :returns: A :class:`ColumnSpec`, or ``None`` if the row has fewer than 4
        populated cells (e.g. a stray blank line inside the table).
    """
    if len(cells) < 4 or not cells[0]:
        return None

    col_name = cells[0]
    raw_api = cells[1]
    pg_type = cells[2].upper()
    required = cells[3].lower() == "yes"
    default: str | None = cells[4].strip() if len(cells) > 4 and cells[4].strip() else None

    # Parse API aliases: "stateId; state_id; stateid"
    api_parts = [p.strip() for p in raw_api.split(";") if p.strip()]
    api_field = api_parts[0] if api_parts else col_name
    api_aliases = api_parts[1:] if len(api_parts) > 1 else []

    return ColumnSpec(
        name=col_name,
        api_field=api_field,
        pg_type=pg_type,
        required=required,
        api_aliases=api_aliases,
        default=default,
    )


def _parse_unique_key(value: str) -> tuple[str, ...]:
    """Parse a unique-key expression like ``(period, stateid, sectorid)``.

    :param value: The raw string value from the spec line, e.g.
        ``"(period, stateid, sectorid)"`` or just ``"period, stateid"``.
    :returns: A tuple of stripped column name strings.
    """
    # Extract contents of parentheses if present
    m = _KEY_RE.search(value)
    inner = m.group(1) if m else value
    return tuple(s.strip() for s in inner.split(",") if s.strip())


def _parse_extra_params(value: str) -> dict[str, str]:
    """Parse a comma-separated list of ``key=value`` pairs.

    :param value: Raw string, e.g. ``"frequency=annual, facets=stateid"``.
    :returns: Dict mapping each key to its value.
    """
    result: dict[str, str] = {}
    for pair in value.split(","):
        pair = pair.strip()
        if "=" in pair:
            k, _, v = pair.partition("=")
            result[k.strip()] = v.strip()
    return result
