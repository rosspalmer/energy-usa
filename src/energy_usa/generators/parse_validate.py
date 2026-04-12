"""Markdown parser for validation spec files.

Converts a ``specs/validate/<source>.md`` file into a
:class:`~energy_usa.generators.models_validate.ValidateSpec` ready for
consumption by the code-generation template
(:mod:`energy_usa.generators.validate`).

Supported spec format
---------------------
::

    # EIA Validation Rules

    ## retail_sales
    - **Date range**: 2001-01 to present
    - **Expected row count**: ~50 rows/month
    - **Null tolerance**:
      | Column | Max null % |
      |--------|-----------|
      | revenue | 5 |
    - **Completeness**: Every stateid should have data for every month
    - **Staleness**: Most recent period within 3 months of today

Key parsing rules
-----------------
- Source name: first word of the H1 heading, lowercased.
- Each ``## name`` starts a dataset section; everything until the next ``##``
  or EOF belongs to that dataset.
- ``**Date range**`` — the first ``YYYY-MM`` in the value is the start date.
- ``**Null tolerance**`` — triggers table-parsing mode; each non-header,
  non-separator row contributes one :class:`NullToleranceSpec`.
- ``**Completeness**`` — ``"Every <dim>"`` gives the dimension list;
  ``"every <freq>"`` (second occurrence) gives the frequency.
- ``**Staleness**`` — ``"within N months"`` sets ``staleness_months``.
- ``**Expected row count**`` — raw value stored as-is.
"""

from __future__ import annotations

import re
from pathlib import Path

from energy_usa.generators.models_validate import (
    DatasetValidationSpec,
    NullToleranceSpec,
    ValidateSpec,
)

# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

# "2001-01" or "2001-1"
_YEAR_MONTH_RE = re.compile(r"\b(\d{4}-\d{1,2})\b")

# "within N months"
_STALENESS_RE = re.compile(r"within\s+(\d+)\s+months?", re.IGNORECASE)

# "Every stateid should ..."  — captures the word(s) after "Every"
_COMPLETENESS_DIM_RE = re.compile(r"every\s+(\w+)", re.IGNORECASE)

# "for every month" / "for every year"
_COMPLETENESS_FREQ_RE = re.compile(r"for\s+every\s+(\w+)", re.IGNORECASE)

# Bold label in a list item: "- **Label**: value" or "  - **Label**:"
_BOLD_LABEL_RE = re.compile(r"\*\*([^*]+)\*\*\s*:?\s*(.*)")


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def parse_validate_spec(text: str) -> ValidateSpec:
    """Parse a validation spec markdown string and return a :class:`ValidateSpec`.

    :param text: Full contents of a ``specs/validate/*.md`` file.
    :returns: A fully populated :class:`ValidateSpec`.
    :raises ValueError: If no H1 heading is found.
    """
    lines = text.splitlines()
    source = _parse_source_name(lines)
    datasets = _parse_dataset_sections(lines)
    return ValidateSpec(source=source, datasets=datasets)


def parse_validate_spec_file(path: Path) -> ValidateSpec:
    """Parse a validation spec markdown file.

    :param path: Absolute or relative path to a ``.md`` validation spec file.
    :returns: A fully populated :class:`ValidateSpec`.
    :raises FileNotFoundError: If ``path`` does not exist.
    :raises ValueError: If the file has no H1 heading.
    """
    return parse_validate_spec(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_source_name(lines: list[str]) -> str:
    """Extract the source name from the H1 heading.

    Takes the first word of the heading and lowercases it.  For example::

        # EIA Validation Rules   →   "eia"
        # Natural Gas            →   "natural"

    :param lines: All lines of the spec file.
    :returns: Lowercase source identifier.
    :raises ValueError: If no H1 heading is found.
    """
    for line in lines:
        if line.startswith("# "):
            heading = line[2:].strip()
            return heading.split()[0].lower() if heading.split() else heading.lower()
    raise ValueError("No H1 heading found in validation spec")


def _parse_dataset_sections(lines: list[str]) -> list[DatasetValidationSpec]:
    """Parse all ``## dataset_name`` sections.

    :param lines: All lines of the spec file.
    :returns: Ordered list of :class:`DatasetValidationSpec` objects.
    """
    datasets: list[DatasetValidationSpec] = []
    current_name: str | None = None
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip()

        # H1 headings are the file title — skip
        if stripped.startswith("# ") and not stripped.startswith("## "):
            continue

        if stripped.startswith("## "):
            # Flush previous dataset
            if current_name is not None:
                datasets.append(_parse_one_dataset(current_name, current_lines))
            current_name = stripped[3:].strip()
            current_lines = []
        elif current_name is not None:
            current_lines.append(line)

    # Flush the last dataset
    if current_name is not None:
        datasets.append(_parse_one_dataset(current_name, current_lines))

    return datasets


def _parse_one_dataset(name: str, lines: list[str]) -> DatasetValidationSpec:
    """Parse the body lines of a single ``## dataset_name`` block.

    :param name: Dataset name (from the ``##`` heading text).
    :param lines: Lines following the heading up to the next heading or EOF.
    :returns: A populated :class:`DatasetValidationSpec`.
    """
    date_range_start = ""
    expected_row_count = ""
    null_tolerances: list[NullToleranceSpec] = []
    completeness_dimensions: list[str] = []
    completeness_frequency = "monthly"
    staleness_months = 0
    range_checks: list[dict] = []

    # State machine for multi-line null-tolerance table
    in_null_table = False
    null_header_seen = False
    null_separator_seen = False

    for line in lines:
        stripped = line.strip()

        # Detect bold-label items
        m = _BOLD_LABEL_RE.search(stripped)
        if m and not stripped.startswith("|"):
            label = m.group(1).strip().lower()
            value = m.group(2).strip()

            if label == "date range":
                year_months = _YEAR_MONTH_RE.findall(value)
                if year_months:
                    date_range_start = year_months[0]
                in_null_table = False

            elif label == "expected row count":
                expected_row_count = value
                in_null_table = False

            elif label == "null tolerance":
                # Table follows on subsequent lines
                in_null_table = True
                null_header_seen = False
                null_separator_seen = False

            elif label == "completeness":
                in_null_table = False
                # "Every stateid should have data for every month"
                dim_matches = _COMPLETENESS_DIM_RE.findall(value)
                # First match is the dimension name ("Every <dim>")
                if dim_matches:
                    completeness_dimensions = [dim_matches[0]]
                # "for every <freq>" — second "every" in the sentence
                freq_match = _COMPLETENESS_FREQ_RE.search(value)
                if freq_match:
                    completeness_frequency = freq_match.group(1).lower()
                    # Normalise "month" → "monthly", "year" → "annual"
                    completeness_frequency = _normalise_frequency(completeness_frequency)

            elif label == "staleness":
                in_null_table = False
                s_match = _STALENESS_RE.search(value)
                if s_match:
                    staleness_months = int(s_match.group(1))

            else:
                in_null_table = False

            continue  # bold-label line handled

        # Parse null-tolerance table rows
        if in_null_table and stripped.startswith("|"):
            cells = _split_table_row(stripped)

            if not null_header_seen:
                null_header_seen = True
                continue  # skip header

            if not null_separator_seen:
                if all(re.match(r"^[-:]+$", c) for c in cells if c):
                    null_separator_seen = True
                    continue

            # Data row: | column_name | max_null_pct |
            if len(cells) >= 2 and cells[0] and cells[1]:
                try:
                    null_tolerances.append(
                        NullToleranceSpec(
                            column=cells[0],
                            max_null_pct=float(cells[1]),
                        )
                    )
                except ValueError:
                    pass  # skip malformed rows silently

    return DatasetValidationSpec(
        name=name,
        date_range_start=date_range_start,
        null_tolerances=null_tolerances,
        expected_row_count=expected_row_count,
        completeness_dimensions=completeness_dimensions,
        completeness_frequency=completeness_frequency,
        staleness_months=staleness_months,
        range_checks=range_checks,
    )


def _split_table_row(row: str) -> list[str]:
    """Split a ``|``-delimited Markdown table row into stripped cell strings.

    :param row: A single Markdown table row.
    :returns: List of stripped cell strings (empty edge cells omitted).
    """
    return [c.strip() for c in row.strip("|").split("|")]


def _normalise_frequency(word: str) -> str:
    """Normalise a singular frequency word to its canonical form.

    :param word: A frequency word such as ``"month"``, ``"year"``,
        ``"monthly"``, or ``"annual"``.
    :returns: Canonical form: ``"monthly"``, ``"annual"``, or the original
        word if no mapping is found.
    """
    mapping = {
        "month": "monthly",
        "monthly": "monthly",
        "year": "annual",
        "yearly": "annual",
        "annual": "annual",
    }
    return mapping.get(word.lower(), word.lower())
