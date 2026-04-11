"""Typed data models for parsed spec files.

These dataclasses are the single source of truth that flows between the
markdown parser (``parse_spec``) and the code-generation templates (Tasks
4-5).  Every generator template receives one of these objects; every parser
test asserts against these types.

Design notes
------------
- Plain :mod:`dataclasses` (no Pydantic) — no runtime validation overhead,
  no extra dependency, and the templates only need attribute access.
- ``field(default_factory=...)`` is used for mutable defaults to avoid the
  classic shared-list bug.
- Properties are pure derivations so templates can call them without
  conditional logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ColumnSpec:
    """Specification for a single database column and its API mapping.

    :param name: The Postgres column name (snake_case), e.g. ``"stateid"``.
    :param api_field: The primary field name as returned by the API response,
        e.g. ``"stateId"``.  This is the first name tried when extracting a
        value from an API row dict.
    :param pg_type: The Postgres data type string in uppercase, e.g.
        ``"DATE"``, ``"TEXT"``, ``"NUMERIC"``, ``"TIMESTAMPTZ"``.
    :param required: When ``True`` the column is ``NOT NULL`` in the schema
        and the ingest code will reject rows missing this field.
    :param api_aliases: Zero or more alternative API field names tried in
        order after ``api_field`` fails.  Useful when the EIA API returns
        different casing across endpoints (e.g. ``["state_id", "stateid"]``).
    :param default: SQL literal or Python value used when all API field
        lookups return ``None``.  ``None`` here means no default — missing
        data propagates as ``NULL``.
    """

    name: str
    api_field: str
    pg_type: str
    required: bool
    api_aliases: list[str] = field(default_factory=list)
    default: str | None = None

    @property
    def is_numeric(self) -> bool:
        """Return ``True`` when the column holds a numeric measurement.

        Numeric columns are singled out because:

        - They are passed as the ``data[]`` query parameter to the EIA API.
        - They receive ``NUMERIC`` (arbitrary-precision) storage, not text.
        - Templates emit ``EXCLUDED.<col>`` for numeric columns in upserts
          so that re-runs refresh measurement values without touching keys.
        """
        return self.pg_type.upper() == "NUMERIC"

    @property
    def all_api_fields(self) -> list[str]:
        """Return the full ordered list of API field names to try.

        The primary ``api_field`` is always first, followed by any
        ``api_aliases`` in the order they were declared in the spec.

        :returns: A new list ``[api_field] + api_aliases``.
        """
        return [self.api_field] + self.api_aliases


@dataclass
class FilterSpec:
    """A row-level filter applied during ingest to exclude unwanted records.

    Currently only equality (``field = 'value'``) is supported, which is
    enough for the common EIA pattern of excluding aggregate rows like
    ``stateid = 'US'``.

    :param field: The API response field name to test.
    :param operator: Comparison operator string.  Always ``"="`` for now;
        future values might include ``"!="`` or ``"in"``.
    :param value: The string value to compare against (without quotes).
    """

    field: str
    operator: str  # "=" for now
    value: str


@dataclass
class DatasetSpec:
    """Complete specification for one EIA dataset / Postgres table.

    A ``DatasetSpec`` fully describes:

    - How to fetch data from the API (``api_path``, ``api_method``,
      ``frequency``, ``extra_api_params``).
    - How to store it in Postgres (``unique_key``, ``columns``, ``indexes``).
    - How far back to pull historical data (``history_start``).
    - Which rows to discard (``filters``).

    :param name: Snake-case identifier matching the Postgres table name, e.g.
        ``"retail_sales"`` → ``eia.retail_sales``.
    :param api_path: URL path fragment appended to the source base URL, e.g.
        ``"/electricity/retail-sales"`` or ``"co2-emissions/.../data"``.
    :param api_method: Logical method name understood by the client, e.g.
        ``"electricity"`` or ``"route"``.  Used by the Prefect flow template
        to dispatch the correct client call.
    :param frequency: Cadence string as returned by the EIA API: ``"monthly"``,
        ``"annual"``, ``"quarterly"``, ``"daily"``, or ``"hourly"``.
    :param unique_key: Column names that form the natural primary key, e.g.
        ``("period", "stateid", "sectorid")``.  Used in ``ON CONFLICT``
        clauses and index DDL.
    :param columns: Ordered list of all columns, including key columns.
    :param filters: Row-level exclusion rules applied during ingest.
    :param history_start: ISO month/year string (``"YYYY-MM"``) of the
        earliest period to request during a full backfill.
    :param extra_api_params: Additional key/value query parameters forwarded
        verbatim to every API request, e.g. ``{"frequency": "annual"}``.
    :param indexes: Extra Postgres index definitions beyond the primary key,
        e.g. ``["stateid"]``.
    """

    name: str
    api_path: str
    api_method: str
    frequency: str
    unique_key: tuple[str, ...]
    columns: list[ColumnSpec]
    filters: list[FilterSpec]
    history_start: str
    extra_api_params: dict[str, str] = field(default_factory=dict)
    indexes: list[str] = field(default_factory=list)

    @property
    def period_type(self) -> str:
        """Translate ``frequency`` into the period-type string used internally.

        The EIA API uses ``"annual"`` but our internal helpers and the Prefect
        flow templates use ``"yearly"`` (matches :func:`normalize_period`).
        All other frequencies pass through unchanged.

        :returns: ``"yearly"`` if ``frequency == "annual"``, else ``frequency``.
        """
        return "yearly" if self.frequency == "annual" else self.frequency

    @property
    def uses_year_only_dates(self) -> bool:
        """Return ``True`` for frequencies where periods are stored as ``YYYY-01-01``.

        Annual data arrives as plain year strings (``"2023"``) rather than
        ``"YYYY-MM"`` or ``"YYYY-MM-DD"``.  The upsert module needs to know
        this to call :func:`normalize_period` with the correct cadence.

        :returns: ``True`` only when ``frequency`` is ``"annual"``.
        """
        return self.frequency in ("annual",)

    @property
    def non_key_columns(self) -> list[ColumnSpec]:
        """Return columns that are NOT part of the unique key.

        These are the columns that appear in the ``SET`` clause of an upsert.
        Key columns are never updated on conflict — only measurement/attribute
        columns are refreshed.

        :returns: A filtered list preserving the original column order.
        """
        key_set = set(self.unique_key)
        return [c for c in self.columns if c.name not in key_set]

    @property
    def data_columns(self) -> list[ColumnSpec]:
        """Columns requested from the API ``data[]`` parameter.

        The EIA API v2 requires callers to enumerate the measurement fields
        they want via ``data[]=field1&data[]=field2``.  Only non-key
        ``NUMERIC`` columns qualify — text metadata fields come back
        automatically without being listed.

        :returns: Non-key columns whose ``pg_type`` is ``NUMERIC``.
        """
        key_set = set(self.unique_key)
        return [
            c
            for c in self.columns
            if c.name not in key_set and c.is_numeric
        ]


@dataclass
class SourceSpec:
    """Top-level specification for a data source and all its datasets.

    A single ``SourceSpec`` corresponds to one markdown spec file, e.g.
    ``specs/ingest/eia.md``.  It holds connection metadata and owns the
    list of :class:`DatasetSpec` objects parsed from the ``## Datasets``
    section.

    :param name: Short lowercase identifier, e.g. ``"eia"``.  Derived from
        the H1 heading of the spec file.
    :param base_url: API root URL, e.g. ``"https://api.eia.gov/v2"``.
    :param api_key_env: Name of the environment variable that holds the API
        key, e.g. ``"EIA_API_KEY"``.
    :param max_concurrent: Maximum number of simultaneous in-flight HTTP
        requests (concurrency semaphore size).
    :param page_delay: Seconds to wait between paginated requests for the
        same dataset, as a float (e.g. ``0.5`` for 500 ms).
    :param datasets: All datasets declared in this spec file, in document
        order.
    """

    name: str
    base_url: str
    api_key_env: str
    max_concurrent: int
    page_delay: float
    datasets: list[DatasetSpec]

    def get_dataset(self, name: str) -> DatasetSpec | None:
        """Look up a dataset by its snake-case name.

        Useful in tests and generator scripts when you need to retrieve one
        specific dataset without iterating manually.

        :param name: The ``DatasetSpec.name`` to search for.
        :returns: The matching :class:`DatasetSpec`, or ``None`` if not found.
        """
        for ds in self.datasets:
            if ds.name == name:
                return ds
        return None
