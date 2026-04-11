# Generator System & EIA Ingest Spec — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the markdown-to-code generator system (spec parser + Jinja2 templates + CLI) and write the EIA ingest spec that documents all 35 existing datasets, so adding new datasets is done by editing a markdown file and running `make generate-ingest`.

**Architecture:** The generator is a development-time tool, not a runtime dependency. A line-based markdown parser extracts structured data into Python dataclasses. Jinja2 templates render those dataclasses into SQL DDL, Python upsert modules, and Prefect flow modules. The EIA ingest spec captures all dataset-specific configuration (API paths, columns, frequencies, filters) in a single markdown file.

**Tech Stack:** Python 3.12, Jinja2, pytest, uv

**Design Spec:** `docs/superpowers/specs/2026-04-10-markdown-driven-data-platform-design.md`

**Depends on:** Plan 1 (schema migration + code restructuring) — complete and merged to main.

---

## File Map

### Created
```
specs/README.md
specs/ingest/_template.md
specs/ingest/eia.md                              # All 35 EIA datasets
specs/validate/_template.md
specs/transform/_template.md
specs/visualize/_template.md
src/energy_usa/generators/__init__.py
src/energy_usa/generators/models.py              # Dataclasses for parsed specs
src/energy_usa/generators/parse_spec.py          # Markdown → dataclasses
src/energy_usa/generators/ingest.py              # Orchestrates generation
src/energy_usa/generators/templates/schema.sql.j2
src/energy_usa/generators/templates/db_module.py.j2
src/energy_usa/generators/templates/flow_module.py.j2
tests/unit/generators/__init__.py
tests/unit/generators/test_models.py
tests/unit/generators/test_parse_spec.py
tests/unit/generators/test_ingest.py
```

### Modified
```
Makefile                                          # Add generate-ingest target
CLAUDE.md                                         # Add generator commands
```

---

## Task 1: Specs Directory Structure

Create the `specs/` directory with README and template files for all four layers.

**Files:**
- Create: `specs/README.md`
- Create: `specs/ingest/_template.md`
- Create: `specs/validate/_template.md`
- Create: `specs/transform/_template.md`
- Create: `specs/visualize/_template.md`

- [ ] **Step 1: Create specs/README.md**

```markdown
# Data Product Specs

Markdown specifications that drive code generation. Each layer has its own
directory, format, and automation level.

| Layer | Automation | Directory | What Claude does |
|-------|-----------|-----------|-----------------|
| Ingest | A (full generation) | `ingest/` | Reads spec, runs generator, produces all code |
| Validate | A (full generation) | `validate/` | Generates validation flows and audit rules |
| Transform | B (scaffold + fill) | `transform/` | Generates skeleton, fills business logic with review |
| Visualize | C (interactive) | `visualize/` | Reads spec as conversation starter, builds interactively |

## Quick Start

```bash
# Generate ingest code for all EIA datasets
make generate-ingest SOURCE=eia

# Generate a single dataset
make generate-ingest SOURCE=eia DATASET=retail_sales
```

## Spec Format Reference

Each `_template.md` file in a layer's directory shows the expected format
with comments explaining each field. Copy it to create a new spec.

## Design Spec

See `docs/superpowers/specs/2026-04-10-markdown-driven-data-platform-design.md`
for the full architecture and rationale.
```

- [ ] **Step 2: Create specs/ingest/_template.md**

```markdown
# <SOURCE_NAME> — <Full Name of Data Source>

## Source
- **Type**: rest-json
- **Base URL**: https://api.example.gov/v2
- **Auth**: API key via query param `api_key`, env var `<SOURCE>_API_KEY`
- **Pagination**: offset-based, `offset` + `length` params, response `total` field
- **Rate limit**: 4 concurrent requests, 100ms page delay

## Datasets

### <dataset_name>
- **API path**: /category/subcategory/data
- **API method**: route
- **Frequency**: monthly
- **Unique key**: (period, stateid, sectorid)
- **Columns**:
  | Column | API field | Type | Required | Default |
  |--------|-----------|------|----------|---------|
  | period | period | DATE | yes | |
  | stateid | stateid | TEXT | yes | |
  | value | value | NUMERIC | no | |
- **Filters**: Skip rows where stateid = 'US'
- **History**: 2001-01
```

- [ ] **Step 3: Create the other three template files**

`specs/validate/_template.md`:
```markdown
# <SOURCE_NAME> Validation Rules

## <dataset_name>
- **Date range**: YYYY-MM to present
- **Expected row count**: ~N rows/month
- **Null tolerance**:
  | Column | Max null % |
  |--------|-----------|
  | column_name | 5 |
- **Completeness**: Every state should have data for every month
- **Staleness**: Most recent period within 3 months of today
```

`specs/transform/_template.md`:
```markdown
# <Domain Name> Domain Model

## <schema>.<table_name>
<Plain-English description of what this table represents.>

- **Source tables**: eia.table_a, eia.table_b
- **Grain**: state + month
- **Join logic**: Match on stateid + period
- **Output columns**:
  | Column | Source | Logic |
  |--------|--------|-------|
  | state | eia.table_a.stateid | direct |
  | period | eia.table_a.period | direct |
  | derived_col | derived | col_a / col_b |
- **Unique key**: (state, period)
```

`specs/visualize/_template.md`:
```markdown
# <Dashboard Name>

## Audience
<Who uses this dashboard and what decisions they make with it.>

## Key questions
1. <Question this dashboard answers>
2. <Another question>

## Data sources
- transform.<schema>.<table>

## Suggested visualizations
- <Chart type>: <description>, filterable by <dimension>
```

- [ ] **Step 4: Commit**

```bash
git add specs/
git commit -m "add specs/ directory with README and layer templates

Four template files (ingest, validate, transform, visualize) document
the markdown spec format for each layer's automation level."
```

---

## Task 2: Spec Dataclasses

Define the typed data model that the parser produces and the templates consume.

**Files:**
- Create: `src/energy_usa/generators/__init__.py`
- Create: `src/energy_usa/generators/models.py`
- Test: `tests/unit/generators/test_models.py`

- [ ] **Step 1: Write tests for the dataclasses**

```python
# tests/unit/generators/test_models.py
"""Tests for generator data models."""

from energy_usa.generators.models import (
    ColumnSpec,
    DatasetSpec,
    FilterSpec,
    SourceSpec,
)


def test_column_spec_required():
    col = ColumnSpec(name="period", api_field="period", pg_type="DATE", required=True)
    assert col.name == "period"
    assert col.required is True
    assert col.api_aliases == []
    assert col.default is None


def test_column_spec_with_aliases_and_default():
    col = ColumnSpec(
        name="state_id",
        api_field="stateId",
        pg_type="TEXT",
        required=True,
        api_aliases=["state_id", "stateid"],
        default="US",
    )
    assert col.api_field == "stateId"
    assert col.api_aliases == ["state_id", "stateid"]
    assert col.default == "US"


def test_column_spec_is_numeric():
    assert ColumnSpec(name="v", api_field="v", pg_type="NUMERIC", required=False).is_numeric
    assert not ColumnSpec(name="v", api_field="v", pg_type="TEXT", required=False).is_numeric
    assert not ColumnSpec(name="v", api_field="v", pg_type="DATE", required=False).is_numeric


def test_filter_spec():
    f = FilterSpec(field="stateid", operator="=", value="US")
    assert f.field == "stateid"
    assert f.value == "US"


def test_dataset_spec_unique_key_columns():
    ds = DatasetSpec(
        name="retail_sales",
        api_path="/electricity/retail-sales",
        api_method="electricity",
        frequency="monthly",
        unique_key=("period", "stateid", "sectorid"),
        columns=[
            ColumnSpec(name="period", api_field="period", pg_type="DATE", required=True),
            ColumnSpec(name="stateid", api_field="stateid", pg_type="TEXT", required=True),
            ColumnSpec(name="sectorid", api_field="sectorid", pg_type="TEXT", required=True),
            ColumnSpec(name="revenue", api_field="revenue", pg_type="NUMERIC", required=False),
        ],
        filters=[],
        history_start="2001-01",
    )
    assert ds.non_key_columns == [ds.columns[3]]
    assert ds.data_columns == [ds.columns[3]]
    assert ds.period_type == "monthly"


def test_dataset_spec_annual_uses_year_only():
    ds = DatasetSpec(
        name="co2",
        api_path="/co2-emissions/data",
        api_method="route",
        frequency="annual",
        unique_key=("period",),
        columns=[ColumnSpec(name="period", api_field="period", pg_type="DATE", required=True)],
        filters=[],
        history_start="2000-01",
    )
    assert ds.period_type == "yearly"
    assert ds.uses_year_only_dates is True


def test_source_spec():
    src = SourceSpec(
        name="eia",
        base_url="https://api.eia.gov/v2",
        api_key_env="EIA_API_KEY",
        max_concurrent=4,
        page_delay=0.5,
        datasets=[],
    )
    assert src.name == "eia"
    assert src.api_key_env == "EIA_API_KEY"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/generators/test_models.py -v
```

Expected: ModuleNotFoundError

- [ ] **Step 3: Implement the dataclasses**

```python
# src/energy_usa/generators/__init__.py
"""Code generators for the markdown-driven data platform."""
```

```python
# src/energy_usa/generators/models.py
"""Typed data models for parsed spec files.

These dataclasses represent the structured data extracted from markdown specs.
The parser produces them; the Jinja2 templates consume them.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ColumnSpec:
    """A single column in a dataset table."""

    name: str
    """Postgres column name (snake_case)."""

    api_field: str
    """Primary API field name as returned by the source."""

    pg_type: str
    """Postgres type: DATE, TEXT, NUMERIC, TIMESTAMPTZ, etc."""

    required: bool
    """Whether the column is NOT NULL in the schema."""

    api_aliases: list[str] = field(default_factory=list)
    """Alternative API field names to try (for case-insensitive mapping)."""

    default: str | None = None
    """Default value if all API fields are None (e.g. 'US', 'ALL')."""

    @property
    def is_numeric(self) -> bool:
        """Whether this column should use safe_numeric() for conversion."""
        return self.pg_type.upper() == "NUMERIC"

    @property
    def all_api_fields(self) -> list[str]:
        """Primary field followed by aliases, for generating fallback lookups."""
        return [self.api_field] + self.api_aliases


@dataclass
class FilterSpec:
    """A row-level filter: skip rows matching this condition."""

    field: str
    """API field name to check."""

    operator: str
    """Comparison operator (= for now, extensible later)."""

    value: str
    """Value to compare against."""


@dataclass
class DatasetSpec:
    """A single dataset within a source."""

    name: str
    """Dataset identifier (snake_case, becomes table name)."""

    api_path: str
    """API endpoint path (e.g. '/electricity/retail-sales' or 'co2-emissions/co2-emissions-aggregates/data')."""

    api_method: str
    """Which EIAManager method to call: 'electricity', 'natural_gas', 'petroleum', 'coal', 'total_energy', or 'route'."""

    frequency: str
    """Data frequency: 'monthly', 'annual', 'quarterly', 'daily', 'hourly'."""

    unique_key: tuple[str, ...]
    """Column names forming the primary key / upsert conflict target."""

    columns: list[ColumnSpec]
    """All columns including period and key columns."""

    filters: list[FilterSpec]
    """Row-level filters (e.g. skip national aggregates)."""

    history_start: str
    """Earliest available data period (YYYY-MM or YYYY)."""

    extra_api_params: dict[str, str] = field(default_factory=dict)
    """Additional API query params (e.g. {'frequency': 'annual'})."""

    indexes: list[str] = field(default_factory=list)
    """Additional index definitions (raw SQL after CREATE INDEX)."""

    @property
    def period_type(self) -> str:
        """Cadence string for normalize_period(): monthly, yearly, daily, quarterly."""
        return "yearly" if self.frequency == "annual" else self.frequency

    @property
    def uses_year_only_dates(self) -> bool:
        """Whether API start/end params should be stripped to YYYY."""
        return self.frequency in ("annual",)

    @property
    def non_key_columns(self) -> list[ColumnSpec]:
        """Columns not in the primary key (updated on conflict)."""
        key_set = set(self.unique_key)
        return [c for c in self.columns if c.name not in key_set]

    @property
    def data_columns(self) -> list[ColumnSpec]:
        """Columns requested from the API data[] param (non-key, non-period, non-text-id columns)."""
        key_set = set(self.unique_key)
        return [c for c in self.columns if c.name not in key_set and c.is_numeric]


@dataclass
class SourceSpec:
    """A data source with its connection details and datasets."""

    name: str
    """Source identifier (e.g. 'eia')."""

    base_url: str
    """API base URL."""

    api_key_env: str
    """Environment variable name for the API key."""

    max_concurrent: int
    """Maximum concurrent API requests."""

    page_delay: float
    """Delay between pagination requests in seconds."""

    datasets: list[DatasetSpec]
    """All datasets for this source."""

    def get_dataset(self, name: str) -> DatasetSpec | None:
        """Look up a dataset by name."""
        for ds in self.datasets:
            if ds.name == name:
                return ds
        return None
```

- [ ] **Step 4: Create test __init__.py**

```bash
mkdir -p tests/unit/generators
touch tests/unit/generators/__init__.py
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/unit/generators/test_models.py -v
```

Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add src/energy_usa/generators/ tests/unit/generators/
git commit -m "add generator data models (ColumnSpec, DatasetSpec, SourceSpec)

Typed dataclasses representing parsed spec data. The parser produces
these; Jinja2 templates consume them. Includes computed properties
for period type, year-only dates, key vs non-key columns."
```

---

## Task 3: Spec Parser

Parse the markdown ingest spec format into `SourceSpec` and `DatasetSpec` dataclasses.

**Files:**
- Create: `src/energy_usa/generators/parse_spec.py`
- Test: `tests/unit/generators/test_parse_spec.py`

- [ ] **Step 1: Write parser tests**

```python
# tests/unit/generators/test_parse_spec.py
"""Tests for the markdown spec parser."""

import textwrap

from energy_usa.generators.parse_spec import parse_ingest_spec


MINIMAL_SPEC = textwrap.dedent("""\
    # EIA — U.S. Energy Information Administration

    ## Source
    - **Type**: rest-json
    - **Base URL**: https://api.eia.gov/v2
    - **Auth**: API key via query param `api_key`, env var `EIA_API_KEY`
    - **Pagination**: offset-based, `offset` + `length` params, response `total` field
    - **Rate limit**: 4 concurrent requests, 500ms page delay

    ## Datasets

    ### retail_sales
    - **API path**: /electricity/retail-sales
    - **API method**: electricity
    - **Frequency**: monthly
    - **Unique key**: (period, stateid, sectorid)
    - **Columns**:
      | Column | API field | Type | Required | Default |
      |--------|-----------|------|----------|---------|
      | period | period | DATE | yes | |
      | stateid | stateid | TEXT | yes | |
      | sectorid | sectorid | TEXT | yes | |
      | revenue | revenue | NUMERIC | no | |
      | sales | sales | NUMERIC | no | |
      | price | price | NUMERIC | no | |
      | customers | customers | NUMERIC | no | |
    - **Filters**: Skip rows where stateid = 'US'
    - **History**: 2001-01
""")


def test_parse_source_metadata():
    spec = parse_ingest_spec(MINIMAL_SPEC)
    assert spec.name == "eia"
    assert spec.base_url == "https://api.eia.gov/v2"
    assert spec.api_key_env == "EIA_API_KEY"
    assert spec.max_concurrent == 4
    assert spec.page_delay == 0.5


def test_parse_single_dataset():
    spec = parse_ingest_spec(MINIMAL_SPEC)
    assert len(spec.datasets) == 1
    ds = spec.datasets[0]
    assert ds.name == "retail_sales"
    assert ds.api_path == "/electricity/retail-sales"
    assert ds.api_method == "electricity"
    assert ds.frequency == "monthly"
    assert ds.unique_key == ("period", "stateid", "sectorid")
    assert ds.history_start == "2001-01"


def test_parse_columns():
    spec = parse_ingest_spec(MINIMAL_SPEC)
    ds = spec.datasets[0]
    assert len(ds.columns) == 7
    period_col = ds.columns[0]
    assert period_col.name == "period"
    assert period_col.api_field == "period"
    assert period_col.pg_type == "DATE"
    assert period_col.required is True
    revenue_col = ds.columns[3]
    assert revenue_col.name == "revenue"
    assert revenue_col.required is False
    assert revenue_col.is_numeric


def test_parse_filters():
    spec = parse_ingest_spec(MINIMAL_SPEC)
    ds = spec.datasets[0]
    assert len(ds.filters) == 1
    assert ds.filters[0].field == "stateid"
    assert ds.filters[0].value == "US"


MULTI_DATASET_SPEC = textwrap.dedent("""\
    # EIA — U.S. Energy Information Administration

    ## Source
    - **Type**: rest-json
    - **Base URL**: https://api.eia.gov/v2
    - **Auth**: API key via query param `api_key`, env var `EIA_API_KEY`
    - **Pagination**: offset-based, `offset` + `length` params, response `total` field
    - **Rate limit**: 4 concurrent requests, 500ms page delay

    ## Datasets

    ### retail_sales
    - **API path**: /electricity/retail-sales
    - **API method**: electricity
    - **Frequency**: monthly
    - **Unique key**: (period, stateid, sectorid)
    - **Columns**:
      | Column | API field | Type | Required | Default |
      |--------|-----------|------|----------|---------|
      | period | period | DATE | yes | |
      | stateid | stateid | TEXT | yes | |
      | sectorid | sectorid | TEXT | yes | |
      | revenue | revenue | NUMERIC | no | |
    - **History**: 2001-01

    ### co2_emissions
    - **API path**: co2-emissions/co2-emissions-aggregates/data
    - **API method**: route
    - **Frequency**: annual
    - **Extra API params**: frequency=annual
    - **Unique key**: (period, state_id, sector_id, fuel_id)
    - **Columns**:
      | Column | API field | Type | Required | Default |
      |--------|-----------|------|----------|---------|
      | period | period | DATE | yes | |
      | state_id | stateId; state_id; stateid | TEXT | yes | US |
      | sector_id | sectorId; sector_id; sectorid | TEXT | yes | ALL |
      | fuel_id | fuelId; fuel_id; fuelid | TEXT | yes | ALL |
      | value | value | NUMERIC | no | |
    - **History**: 1970-01
""")


def test_parse_multiple_datasets():
    spec = parse_ingest_spec(MULTI_DATASET_SPEC)
    assert len(spec.datasets) == 2
    assert spec.datasets[0].name == "retail_sales"
    assert spec.datasets[1].name == "co2_emissions"


def test_parse_api_aliases():
    spec = parse_ingest_spec(MULTI_DATASET_SPEC)
    co2 = spec.datasets[1]
    state_col = co2.columns[1]
    assert state_col.api_field == "stateId"
    assert state_col.api_aliases == ["state_id", "stateid"]
    assert state_col.default == "US"


def test_parse_annual_frequency():
    spec = parse_ingest_spec(MULTI_DATASET_SPEC)
    co2 = spec.datasets[1]
    assert co2.frequency == "annual"
    assert co2.period_type == "yearly"
    assert co2.uses_year_only_dates is True


def test_parse_extra_api_params():
    spec = parse_ingest_spec(MULTI_DATASET_SPEC)
    co2 = spec.datasets[1]
    assert co2.extra_api_params == {"frequency": "annual"}


def test_parse_from_file(tmp_path):
    spec_file = tmp_path / "eia.md"
    spec_file.write_text(MINIMAL_SPEC)
    spec = parse_ingest_spec(spec_file.read_text())
    assert spec.name == "eia"
    assert len(spec.datasets) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/generators/test_parse_spec.py -v
```

Expected: ImportError

- [ ] **Step 3: Implement the parser**

```python
# src/energy_usa/generators/parse_spec.py
"""Parse markdown ingest specs into typed dataclasses.

The parser is line-based and assumes the rigid format defined in
specs/ingest/_template.md. It does not use a general-purpose markdown
AST — the format is simple enough that line-by-line parsing is clearer.
"""

from __future__ import annotations

import re

from energy_usa.generators.models import (
    ColumnSpec,
    DatasetSpec,
    FilterSpec,
    SourceSpec,
)


def parse_ingest_spec(text: str) -> SourceSpec:
    """Parse a markdown ingest spec into a SourceSpec.

    :param text: Full markdown content of the spec file.
    :returns: Parsed SourceSpec with all datasets.
    """
    lines = text.splitlines()
    source_name = _parse_source_name(lines)
    source_meta = _parse_source_section(lines)
    datasets = _parse_datasets(lines)
    return SourceSpec(
        name=source_name,
        base_url=source_meta["base_url"],
        api_key_env=source_meta["api_key_env"],
        max_concurrent=source_meta["max_concurrent"],
        page_delay=source_meta["page_delay"],
        datasets=datasets,
    )


def _parse_source_name(lines: list[str]) -> str:
    """Extract source name from the H1 heading."""
    for line in lines:
        if line.startswith("# "):
            # "# EIA — U.S. Energy..." → "eia"
            name = line[2:].strip().split("—")[0].split("-")[0].strip()
            return name.lower()
    raise ValueError("No H1 heading found in spec")


def _parse_source_section(lines: list[str]) -> dict:
    """Extract source metadata from the ## Source section."""
    in_source = False
    meta: dict = {
        "base_url": "",
        "api_key_env": "",
        "max_concurrent": 4,
        "page_delay": 0.5,
    }
    for line in lines:
        stripped = line.strip()
        if stripped == "## Source":
            in_source = True
            continue
        if in_source and stripped.startswith("## "):
            break
        if not in_source:
            continue
        if "**Base URL**" in stripped:
            meta["base_url"] = _extract_value(stripped)
        elif "**Auth**" in stripped:
            env_match = re.search(r"env var `(\w+)`", stripped)
            if env_match:
                meta["api_key_env"] = env_match.group(1)
        elif "**Rate limit**" in stripped:
            concurrent_match = re.search(r"(\d+)\s+concurrent", stripped)
            delay_match = re.search(r"(\d+)ms\s+page\s+delay", stripped)
            if concurrent_match:
                meta["max_concurrent"] = int(concurrent_match.group(1))
            if delay_match:
                meta["page_delay"] = int(delay_match.group(1)) / 1000.0
    return meta


def _parse_datasets(lines: list[str]) -> list[DatasetSpec]:
    """Parse all ### dataset sections under ## Datasets."""
    datasets: list[DatasetSpec] = []
    in_datasets = False
    current_block: list[str] = []
    current_name: str | None = None

    for line in lines:
        stripped = line.strip()
        if stripped == "## Datasets":
            in_datasets = True
            continue
        if not in_datasets:
            continue
        if stripped.startswith("## ") and stripped != "## Datasets":
            # Next top-level section — stop
            if current_name and current_block:
                datasets.append(_parse_single_dataset(current_name, current_block))
            break
        if stripped.startswith("### "):
            if current_name and current_block:
                datasets.append(_parse_single_dataset(current_name, current_block))
            current_name = stripped[4:].strip()
            current_block = []
        elif current_name is not None:
            current_block.append(line)

    # Handle last dataset if file ends without another ## section
    if current_name and current_block:
        datasets.append(_parse_single_dataset(current_name, current_block))

    return datasets


def _parse_single_dataset(name: str, block: list[str]) -> DatasetSpec:
    """Parse a single dataset block into a DatasetSpec."""
    api_path = ""
    api_method = "route"
    frequency = "monthly"
    unique_key: tuple[str, ...] = ()
    columns: list[ColumnSpec] = []
    filters: list[FilterSpec] = []
    history_start = ""
    extra_api_params: dict[str, str] = {}
    indexes: list[str] = []

    in_column_table = False
    for line in block:
        stripped = line.strip()

        # Column table parsing
        if in_column_table:
            if stripped.startswith("|") and not stripped.startswith("|--") and not stripped.startswith("| Column"):
                col = _parse_column_row(stripped)
                if col:
                    columns.append(col)
                continue
            elif stripped.startswith("|"):
                continue  # header or separator row
            else:
                in_column_table = False

        if "**Columns**" in stripped:
            in_column_table = True
            continue

        if "**API path**" in stripped:
            api_path = _extract_value(stripped)
        elif "**API method**" in stripped:
            api_method = _extract_value(stripped).lower()
        elif "**Frequency**" in stripped:
            frequency = _extract_value(stripped).lower()
        elif "**Unique key**" in stripped:
            key_str = _extract_value(stripped)
            # "(period, stateid, sectorid)" → ("period", "stateid", "sectorid")
            key_str = key_str.strip("()")
            unique_key = tuple(k.strip() for k in key_str.split(",") if k.strip())
        elif "**History**" in stripped:
            history_start = _extract_value(stripped)
        elif "**Filters**" in stripped:
            filters = _parse_filters(stripped)
        elif "**Extra API params**" in stripped:
            extra_api_params = _parse_extra_params(_extract_value(stripped))
        elif "**Indexes**" in stripped:
            indexes.append(_extract_value(stripped))

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


def _parse_column_row(row: str) -> ColumnSpec | None:
    """Parse a markdown table row into a ColumnSpec."""
    cells = [c.strip() for c in row.split("|")]
    # Remove empty cells from leading/trailing pipes
    cells = [c for c in cells if c]
    if len(cells) < 4:
        return None

    name = cells[0]
    api_field_raw = cells[1]
    pg_type = cells[2].upper()
    required = cells[3].lower() == "yes"
    default = cells[4].strip() if len(cells) > 4 and cells[4].strip() else None

    # Parse API field with aliases: "stateId; state_id; stateid"
    parts = [p.strip() for p in api_field_raw.split(";")]
    api_field = parts[0]
    api_aliases = parts[1:] if len(parts) > 1 else []

    return ColumnSpec(
        name=name,
        api_field=api_field,
        pg_type=pg_type,
        required=required,
        api_aliases=api_aliases,
        default=default,
    )


def _parse_filters(line: str) -> list[FilterSpec]:
    """Parse filter line like 'Skip rows where stateid = 'US''."""
    filters: list[FilterSpec] = []
    value_part = _extract_value(line)
    # Pattern: "Skip rows where <field> = '<value>'"
    match = re.search(r"where\s+(\w+)\s*=\s*'([^']+)'", value_part, re.IGNORECASE)
    if match:
        filters.append(FilterSpec(field=match.group(1), operator="=", value=match.group(2)))
    return filters


def _parse_extra_params(value: str) -> dict[str, str]:
    """Parse 'key=value, key2=value2' into a dict."""
    params: dict[str, str] = {}
    for pair in value.split(","):
        pair = pair.strip()
        if "=" in pair:
            k, v = pair.split("=", 1)
            params[k.strip()] = v.strip()
    return params


def _extract_value(line: str) -> str:
    """Extract value after '**Label**: value' pattern."""
    match = re.search(r"\*\*[^*]+\*\*:\s*(.*)", line)
    return match.group(1).strip() if match else ""
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/unit/generators/test_parse_spec.py -v
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add src/energy_usa/generators/parse_spec.py tests/unit/generators/test_parse_spec.py
git commit -m "add markdown ingest spec parser

Line-based parser extracts Source metadata and Dataset specifications
from the rigid markdown format. Handles column tables with API field
aliases, filters, extra API params, and frequency settings."
```

---

## Task 4: Jinja2 Templates

Write the three templates that produce SQL DDL, Python db modules, and Prefect flow modules.

**Files:**
- Create: `src/energy_usa/generators/templates/schema.sql.j2`
- Create: `src/energy_usa/generators/templates/db_module.py.j2`
- Create: `src/energy_usa/generators/templates/flow_module.py.j2`

- [ ] **Step 1: Write the SQL schema template**

```jinja2
{# src/energy_usa/generators/templates/schema.sql.j2 #}
-- {{ source }}.{{ dataset.name }}: {{ dataset.frequency }} data.
-- Unique on ({{ dataset.unique_key | join(', ') }}) for idempotent upserts.
CREATE TABLE IF NOT EXISTS {{ source }}.{{ dataset.name }} (
{% for col in dataset.columns %}
    {{ col.name }} {{ col.pg_type }}{% if col.required %} NOT NULL{% endif %},
{% endfor %}
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY ({{ dataset.unique_key | join(', ') }})
);
{% for idx in dataset.indexes %}

CREATE INDEX IF NOT EXISTS {{ idx }};
{% endfor %}
```

- [ ] **Step 2: Write the db module template**

```jinja2
{# src/energy_usa/generators/templates/db_module.py.j2 #}
"""Upsert {{ source }}.{{ dataset.name }} rows into Postgres.

{{ dataset.frequency | capitalize }} data.
Unique key: ({{ dataset.unique_key | join(', ') }}).
"""

from typing import Any

import psycopg

{% if dataset.columns | selectattr('is_numeric') | list %}
from energy_usa.db.period import normalize_period, safe_numeric
{% else %}
from energy_usa.db.period import normalize_period
{% endif %}


def upsert_{{ dataset.name }}(conn: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert rows into {{ source }}.{{ dataset.name }}.

    :param conn: Open psycopg connection.
    :param rows: List of dicts from the API.
    :returns: Number of rows upserted.
    """
    if not rows:
        return 0
    sql = """
    INSERT INTO {{ source }}.{{ dataset.name }}
        ({{ dataset.columns | map(attribute='name') | join(', ') }}, ingested_at)
    VALUES
        ({{ dataset.columns | map(attribute='name') | map('format_string', '%({0})s') | join(', ') }}, now())
    ON CONFLICT ({{ dataset.unique_key | join(', ') }})
    DO UPDATE SET
{% for col in dataset.non_key_columns %}
        {{ col.name }} = EXCLUDED.{{ col.name }}{{ "," if not loop.last else "" }}
{% endfor %}
        {% if dataset.non_key_columns %},{% endif %}

        ingested_at = now()
    """
    normalized = []
    for r in rows:
        period_date = normalize_period(r.get("period"), "{{ dataset.period_type }}")
        if period_date is None:
            continue
{% for f in dataset.filters %}
        if r.get("{{ f.field }}") == "{{ f.value }}":
            continue
{% endfor %}
        normalized.append({
            "period": period_date,
{% for col in dataset.columns %}
{% if col.name != 'period' %}
{% if col.is_numeric %}
            "{{ col.name }}": safe_numeric({% for field in col.all_api_fields %}r.get("{{ field }}"){{ " or " if not loop.last else "" }}{% endfor %}),
{% elif col.api_aliases or col.default %}
            "{{ col.name }}": {% for field in col.all_api_fields %}r.get("{{ field }}"){{ " or " if not loop.last or col.default else "" }}{% endfor %}{% if col.default %} or "{{ col.default }}"{% endif %},
{% else %}
            "{{ col.name }}": r.get("{{ col.api_field }}"),
{% endif %}
{% endif %}
{% endfor %}
        })
    if not normalized:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, normalized)
    conn.commit()
    return len(normalized)
```

- [ ] **Step 3: Write the flow module template**

```jinja2
{# src/energy_usa/generators/templates/flow_module.py.j2 #}
"""Prefect flow: fetch and upsert {{ source }}.{{ dataset.name }}.

{{ dataset.frequency | capitalize }} data. Period stored as DATE.
"""

import asyncio
from typing import Any

from prefect import flow, task
from prefect.logging import get_run_logger

from energy_usa.config import Settings
from energy_usa.db.connection import get_connection
from energy_usa.db.ingest.{{ source }}.{{ dataset.name }} import upsert_{{ dataset.name }}
from energy_usa.clients.{{ source }} import EIAManager
from energy_usa.flows.date_range import make_run_name, resolve_date_range

EIA_PAGE_LENGTH = 5000
EIA_{{ dataset.name | upper }}_COLUMNS = {{ dataset.data_columns | map(attribute='name') | list | tojson }}
{% if dataset.api_method == 'route' %}
EIA_{{ dataset.name | upper }}_PATH = "{{ dataset.api_path }}"
{% endif %}


@task(name="fetch-{{ source }}-{{ dataset.name | replace('_', '-') }}")
async def fetch_{{ source }}_{{ dataset.name }}(
    *,
    base_url: str, api_key: str, timeout: float,
    max_concurrent: int, max_retries: int, page_delay_seconds: float = 0.0,
    start: str, end: str,
) -> list[dict[str, Any]]:
    """Fetch {{ source }}.{{ dataset.name }} data via pagination."""
    logger = get_run_logger()
    manager = EIAManager(
        base_url=base_url, api_key=api_key, timeout=timeout,
        max_concurrent=max_concurrent, max_retries=max_retries,
    )
    try:
        all_data: list[dict[str, Any]] = []
        offset = 0
{% if dataset.uses_year_only_dates %}
        start_year = start[:4] if start else ""
        end_year = end[:4] if end else ""
{% endif %}
        while True:
            params: dict[str, Any] = {
                "length": EIA_PAGE_LENGTH, "offset": offset,
                "data[]": EIA_{{ dataset.name | upper }}_COLUMNS,
{% if dataset.uses_year_only_dates %}
                "start": start_year, "end": end_year,
{% else %}
                "start": start, "end": end,
{% endif %}
{% for k, v in dataset.extra_api_params.items() %}
                "{{ k }}": "{{ v }}",
{% endfor %}
            }
{% if dataset.api_method == 'electricity' %}
            resp = await manager.get_electricity(subpath="{{ dataset.api_path }}", **params)
{% elif dataset.api_method == 'route' %}
            resp = await manager.get_route(EIA_{{ dataset.name | upper }}_PATH, **params)
{% else %}
            resp = await manager.get_{{ dataset.api_method }}(subpath="{{ dataset.api_path }}", **params)
{% endif %}
            response_body = resp.get("response") or {}
            data = response_body.get("data")
            if not isinstance(data, list):
                data = []
            if not data:
                break
            all_data.extend(data)
            offset += len(data)
            total_available = response_body.get("total")
            if total_available is not None:
                try:
                    if offset >= int(total_available):
                        break
                except (TypeError, ValueError):
                    logger.warning(
                        "Unexpected 'total' value from API: %r", total_available,
                    )
            if page_delay_seconds > 0:
                await asyncio.sleep(page_delay_seconds)
        logger.info("Fetch complete: total rows=%s", len(all_data))
        return all_data
    finally:
        await manager.aclose()


@task(name="upsert-{{ dataset.name | replace('_', '-') }}")
def upsert_{{ dataset.name }}_task(database_url: str, rows: list[dict[str, Any]]) -> int:
    """Upsert rows into {{ source }}.{{ dataset.name }}."""
    conn = get_connection(database_url)
    try:
        return upsert_{{ dataset.name }}(conn, rows)
    finally:
        conn.close()


def _run_name(**kwargs):
    return make_run_name("{{ dataset.frequency }}", kwargs.get("date_start"), kwargs.get("date_end"))


@flow(
    name="ingest-{{ source }}-{{ dataset.name | replace('_', '-') }}",
    flow_run_name=_run_name,
    retries=2,
    retry_delay_seconds=60,
    timeout_seconds=1800,
)
async def ingest_{{ source }}_{{ dataset.name }}(
    date_start: str | None = None, date_end: str | None = None,
) -> int:
    """Fetch and upsert {{ source }}.{{ dataset.name }}."""
    logger = get_run_logger()
    settings = Settings()
    if not settings.eia_api_key:
        raise ValueError("EIA_API_KEY required")
    if not settings.ingest_database_url:
        raise ValueError("INGEST_DATABASE_URL required")
    start, end = resolve_date_range(date_start, date_end)
    data = await fetch_{{ source }}_{{ dataset.name }}(
        base_url=settings.eia_base_url, api_key=settings.eia_api_key,
        timeout=settings.eia_ingest_timeout_seconds,
        max_concurrent=settings.eia_max_concurrent_requests,
        max_retries=settings.eia_max_retries,
        page_delay_seconds=settings.eia_page_delay_seconds,
        start=start, end=end,
    )
    total = upsert_{{ dataset.name }}_task(settings.ingest_database_url, data)
    if total == 0:
        raise RuntimeError(f"Zero rows upserted for {start}→{end}")
    logger.info("Complete: rows_upserted=%s", total)
    return total
```

- [ ] **Step 2: Commit**

```bash
mkdir -p src/energy_usa/generators/templates
git add src/energy_usa/generators/templates/
git commit -m "add Jinja2 templates for schema, db module, and flow generation

Three templates produce: SQL DDL (CREATE TABLE with PRIMARY KEY),
Python upsert modules (with period normalization, safe_numeric, filters),
and Prefect flows (with pagination, retry, date range handling).
Templates handle electricity vs route API methods, annual vs monthly
frequency, column aliases, and row filters."
```

---

## Task 5: Ingest Generator

Wire the parser and templates together into a generator that reads a spec and writes files.

**Files:**
- Create: `src/energy_usa/generators/ingest.py`
- Test: `tests/unit/generators/test_ingest.py`

- [ ] **Step 1: Write generator tests**

```python
# tests/unit/generators/test_ingest.py
"""Tests for the ingest code generator."""

import textwrap
from pathlib import Path

from energy_usa.generators.ingest import generate_ingest
from energy_usa.generators.parse_spec import parse_ingest_spec

SPEC_TEXT = textwrap.dedent("""\
    # EIA — U.S. Energy Information Administration

    ## Source
    - **Type**: rest-json
    - **Base URL**: https://api.eia.gov/v2
    - **Auth**: API key via query param `api_key`, env var `EIA_API_KEY`
    - **Pagination**: offset-based, `offset` + `length` params, response `total` field
    - **Rate limit**: 4 concurrent requests, 500ms page delay

    ## Datasets

    ### retail_sales
    - **API path**: /electricity/retail-sales
    - **API method**: electricity
    - **Frequency**: monthly
    - **Unique key**: (period, stateid, sectorid)
    - **Columns**:
      | Column | API field | Type | Required | Default |
      |--------|-----------|------|----------|---------|
      | period | period | DATE | yes | |
      | stateid | stateid | TEXT | yes | |
      | sectorid | sectorid | TEXT | yes | |
      | revenue | revenue | NUMERIC | no | |
    - **Filters**: Skip rows where stateid = 'US'
    - **History**: 2001-01
""")


def test_generate_creates_schema_sql(tmp_path):
    spec = parse_ingest_spec(SPEC_TEXT)
    generate_ingest(spec, output_dir=tmp_path, datasets=["retail_sales"])
    sql_file = tmp_path / "docker" / "postgres" / "init" / "ingest" / "eia" / "retail_sales.sql"
    assert sql_file.exists()
    content = sql_file.read_text()
    assert "CREATE TABLE IF NOT EXISTS eia.retail_sales" in content
    assert "PRIMARY KEY (period, stateid, sectorid)" in content
    assert "ingested_at TIMESTAMPTZ" in content


def test_generate_creates_db_module(tmp_path):
    spec = parse_ingest_spec(SPEC_TEXT)
    generate_ingest(spec, output_dir=tmp_path, datasets=["retail_sales"])
    py_file = tmp_path / "src" / "energy_usa" / "db" / "ingest" / "eia" / "retail_sales.py"
    assert py_file.exists()
    content = py_file.read_text()
    assert "def upsert_retail_sales(" in content
    assert "INSERT INTO eia.retail_sales" in content
    assert "ON CONFLICT (period, stateid, sectorid)" in content
    assert 'normalize_period(r.get("period"), "monthly")' in content
    assert 'safe_numeric' in content


def test_generate_creates_flow_module(tmp_path):
    spec = parse_ingest_spec(SPEC_TEXT)
    generate_ingest(spec, output_dir=tmp_path, datasets=["retail_sales"])
    py_file = tmp_path / "src" / "energy_usa" / "flows" / "ingest" / "eia" / "retail_sales.py"
    assert py_file.exists()
    content = py_file.read_text()
    assert "async def ingest_eia_retail_sales(" in content
    assert "manager.get_electricity(" in content
    assert "from energy_usa.db.ingest.eia.retail_sales import upsert_retail_sales" in content


def test_generate_filters_in_db_module(tmp_path):
    spec = parse_ingest_spec(SPEC_TEXT)
    generate_ingest(spec, output_dir=tmp_path, datasets=["retail_sales"])
    py_file = tmp_path / "src" / "energy_usa" / "db" / "ingest" / "eia" / "retail_sales.py"
    content = py_file.read_text()
    assert 'r.get("stateid") == "US"' in content


def test_generate_single_dataset(tmp_path):
    spec = parse_ingest_spec(SPEC_TEXT)
    generate_ingest(spec, output_dir=tmp_path, datasets=["retail_sales"])
    # Only retail_sales should be generated
    db_dir = tmp_path / "src" / "energy_usa" / "db" / "ingest" / "eia"
    py_files = [f.name for f in db_dir.glob("*.py") if f.name != "__init__.py"]
    assert py_files == ["retail_sales.py"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/generators/test_ingest.py -v
```

Expected: ImportError

- [ ] **Step 3: Implement the generator**

```python
# src/energy_usa/generators/ingest.py
"""Generate ingest artifacts (SQL, db module, flow module) from a parsed spec.

This is a development-time tool, not a runtime dependency. It reads a
SourceSpec (produced by the parser) and writes files via Jinja2 templates.
"""

from __future__ import annotations

from pathlib import Path

import jinja2

from energy_usa.generators.models import SourceSpec

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _get_env() -> jinja2.Environment:
    """Create a Jinja2 environment with the templates directory."""
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    # Custom filter for SQL parameter placeholders
    def format_string(value: str, fmt: str) -> str:
        return fmt.format(value)
    env.filters["format_string"] = format_string
    return env


def generate_ingest(
    spec: SourceSpec,
    *,
    output_dir: Path | None = None,
    datasets: list[str] | None = None,
) -> list[Path]:
    """Generate ingest code for a source spec.

    :param spec: Parsed source spec.
    :param output_dir: Root directory for output (defaults to repo root).
    :param datasets: Optional list of dataset names to generate. None = all.
    :returns: List of generated file paths.
    """
    root = output_dir or Path.cwd()
    env = _get_env()
    generated: list[Path] = []

    targets = spec.datasets
    if datasets:
        targets = [d for d in targets if d.name in datasets]

    for ds in targets:
        ctx = {"source": spec.name, "dataset": ds}

        # SQL schema
        sql_path = root / "docker" / "postgres" / "init" / "ingest" / spec.name / f"{ds.name}.sql"
        sql_path.parent.mkdir(parents=True, exist_ok=True)
        sql_path.write_text(env.get_template("schema.sql.j2").render(**ctx))
        generated.append(sql_path)

        # DB module
        db_path = root / "src" / "energy_usa" / "db" / "ingest" / spec.name / f"{ds.name}.py"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.write_text(env.get_template("db_module.py.j2").render(**ctx))
        generated.append(db_path)

        # Flow module
        flow_path = root / "src" / "energy_usa" / "flows" / "ingest" / spec.name / f"{ds.name}.py"
        flow_path.parent.mkdir(parents=True, exist_ok=True)
        flow_path.write_text(env.get_template("flow_module.py.j2").render(**ctx))
        generated.append(flow_path)

    return generated
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/unit/generators/test_ingest.py -v
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add src/energy_usa/generators/ingest.py tests/unit/generators/test_ingest.py
git commit -m "add ingest code generator

Wires spec parser and Jinja2 templates together. generate_ingest()
reads a SourceSpec and writes SQL DDL, Python upsert modules, and
Prefect flow modules for each dataset. Supports generating all
datasets or a filtered subset."
```

---

## Task 6: Makefile Target and CLI Entry Point

Add `make generate-ingest` that reads a spec file and runs the generator.

**Files:**
- Create: `scripts/generate.py`
- Modify: `Makefile`

- [ ] **Step 1: Create the CLI script**

```python
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

from energy_usa.generators.parse_spec import parse_ingest_spec
from energy_usa.generators.ingest import generate_ingest


def cmd_ingest(args: argparse.Namespace) -> None:
    spec_path = Path("specs/ingest") / f"{args.source}.md"
    if not spec_path.exists():
        print(f"ERROR: Spec file not found: {spec_path}")
        sys.exit(1)
    spec = parse_ingest_spec(spec_path.read_text())
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
```

- [ ] **Step 2: Add Makefile targets**

Add after the `export` target in `Makefile`:

```makefile
# ── Code generation ───────────────────────────────────────────────────────────
# Generate ingest artifacts (SQL, db module, flow) from markdown specs.
#
# Examples:
#   make generate-ingest SOURCE=eia
#   make generate-ingest SOURCE=eia DATASET=retail_sales

SOURCE    ?= eia                    # Source for code generation
GDATASET  ?=                        # Dataset for single-dataset generation (blank = all)

generate-ingest:  ## Generate ingest code from specs/ingest/<SOURCE>.md
	uv run python scripts/generate.py ingest \
	  --source $(SOURCE) \
	  $(if $(GDATASET),--dataset $(GDATASET))
```

Also update the `.PHONY` line to include `generate-ingest`.

- [ ] **Step 3: Commit**

```bash
git add scripts/generate.py Makefile
git commit -m "add make generate-ingest CLI and Makefile target

scripts/generate.py reads a markdown spec and runs the ingest generator.
make generate-ingest SOURCE=eia [DATASET=name] wraps the CLI."
```

---

## Task 7: Write the EIA Ingest Spec

Document all 35 existing EIA datasets in the spec format. This is the largest task — it captures every dataset's API path, method, frequency, columns, filters, and aliases by reading the existing code.

**Files:**
- Create: `specs/ingest/eia.md`

- [ ] **Step 1: Write the EIA spec**

Read every existing db module and flow module in `src/energy_usa/db/ingest/eia/` and `src/energy_usa/flows/ingest/eia/` to extract:
- Dataset name
- API path (from the flow's `EIA_*_PATH` constant or `get_electricity(subpath=...)`)
- API method (electricity or route)
- Frequency (from `normalize_period()` cadence in the db module)
- Unique key (from the SQL `ON CONFLICT` clause)
- All columns with their API field names, types, required flags, aliases, and defaults
- Filters (from skip conditions in the db module)
- Extra API params (from the flow's fetch task)
- History start date (from the design spec or EIA documentation)

The resulting file should follow the format in `specs/ingest/_template.md` with the Source section at the top followed by 35 Dataset subsections.

The Source section:
```markdown
# EIA — U.S. Energy Information Administration

## Source
- **Type**: rest-json
- **Base URL**: https://api.eia.gov/v2
- **Auth**: API key via query param `api_key`, env var `EIA_API_KEY`
- **Pagination**: offset-based, `offset` + `length` params, response `total` field
- **Rate limit**: 4 concurrent requests, 500ms page delay

## Datasets
```

Then one `### dataset_name` section per dataset. For example, the retail_sales section was shown in the design spec. Each of the 35 datasets needs its complete definition.

This task requires reading all 35 db modules and 35 flow modules to extract the exact column mappings, API paths, and filter logic. Use the patterns observed in the exploration phase as a guide.

- [ ] **Step 2: Verify the spec parses correctly**

```bash
uv run python -c "
from energy_usa.generators.parse_spec import parse_ingest_spec
from pathlib import Path
spec = parse_ingest_spec(Path('specs/ingest/eia.md').read_text())
print(f'Parsed {len(spec.datasets)} datasets from EIA spec')
for ds in spec.datasets:
    print(f'  {ds.name}: {len(ds.columns)} columns, key=({", ".join(ds.unique_key)})')
"
```

Expected: 35 datasets listed with correct column counts and keys.

- [ ] **Step 3: Commit**

```bash
git add specs/ingest/eia.md
git commit -m "add EIA ingest spec documenting all 35 datasets

Captures API paths, methods, frequencies, columns with aliases,
filters, and extra params for every existing EIA dataset. This is
the source of truth for code generation via make generate-ingest."
```

---

## Task 8: Validation — Regenerate and Diff

Verify the generator produces code that matches the existing hand-written code for a representative dataset.

**Files:** None created — validation only.

- [ ] **Step 1: Generate retail_sales to a temp directory and diff**

```bash
uv run python -c "
from pathlib import Path
from energy_usa.generators.parse_spec import parse_ingest_spec
from energy_usa.generators.ingest import generate_ingest

spec = parse_ingest_spec(Path('specs/ingest/eia.md').read_text())
out = Path('/tmp/gen-test')
generate_ingest(spec, output_dir=out, datasets=['retail_sales'])

# Compare generated vs existing
import difflib
for kind, gen_path, existing_path in [
    ('SQL', out / 'docker/postgres/init/ingest/eia/retail_sales.sql',
     Path('docker/postgres/init/ingest/eia/retail_sales.sql')),
    ('DB', out / 'src/energy_usa/db/ingest/eia/retail_sales.py',
     Path('src/energy_usa/db/ingest/eia/retail_sales.py')),
    ('Flow', out / 'src/energy_usa/flows/ingest/eia/retail_sales.py',
     Path('src/energy_usa/flows/ingest/eia/retail_sales.py')),
]:
    gen = gen_path.read_text().splitlines()
    existing = existing_path.read_text().splitlines()
    diff = list(difflib.unified_diff(existing, gen, fromfile=f'existing/{kind}', tofile=f'generated/{kind}', lineterm=''))
    if diff:
        print(f'\n{kind} DIFFERENCES:')
        for line in diff[:30]:
            print(line)
    else:
        print(f'{kind}: IDENTICAL')
"
```

The generated code will not be identical to the hand-written code — the hand-written code has bespoke docstrings, formatting quirks, and historical artifacts. The goal is that the generated code is **functionally equivalent**: same SQL schema, same upsert logic, same flow structure.

- [ ] **Step 2: Review and iterate on templates**

If the diff shows meaningful differences (not just whitespace or docstring wording), adjust the Jinja2 templates to match the expected pattern more closely. Commit any template fixes.

- [ ] **Step 3: Run the full test suite**

```bash
uv run pytest tests/ -v --ignore=tests/integration
```

Expected: All unit tests pass.

- [ ] **Step 4: Commit any fixes**

```bash
git add src/energy_usa/generators/
git commit -m "refine generator templates after validation diff

Adjusts templates to produce code closer to the existing hand-written
pattern. Generated code is functionally equivalent."
```

---

## Task 9: Update Documentation

Update CLAUDE.md to document the generator system and new Makefile targets.

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add generator info to CLAUDE.md**

In the **Common Commands** section, add:

```markdown
# Code generation (from markdown specs)
make generate-ingest SOURCE=eia                    # All EIA datasets
make generate-ingest SOURCE=eia GDATASET=retail_sales  # Single dataset
```

In the **Key Components** section, add:

```markdown
- `generators/` — Development-time code generation from markdown specs
  - `models.py` — Dataclasses (SourceSpec, DatasetSpec, ColumnSpec)
  - `parse_spec.py` — Markdown parser for ingest specs
  - `ingest.py` — Generates SQL, db modules, and flow modules
  - `templates/` — Jinja2 templates for each output type
- `specs/ingest/eia.md` — Source of truth for all EIA dataset configurations
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "document generator system in CLAUDE.md

Adds generate-ingest command and specs/generators description to
the project guidance file."
```
