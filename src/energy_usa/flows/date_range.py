"""Date range helper for EIA ingest flows.

EIA API v2 electricity data endpoints accept start and end query parameters.
Format is YYYY-MM for monthly series (e.g. retail-sales, state-electricity-profiles).
When date_start or date_end are omitted, default is last calendar month through
the first period of the current month (end = current month) so the API returns rows.
"""

from datetime import date
from typing import Iterator, Tuple


def _parse_period(period: str) -> date:
    """Parse YYYY-MM into a month-start date."""
    try:
        year_str, month_str = period.split("-", maxsplit=1)
        year = int(year_str)
        month = int(month_str)
        return date(year, month, 1)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid period '{period}'. Expected YYYY-MM.") from exc


def _format_period(period: date) -> str:
    """Format month-start date as YYYY-MM."""
    return f"{period.year}-{period.month:02d}"


def _add_months(start: date, months: int) -> date:
    """Return a month-start date plus N months."""
    zero_based = (start.year * 12 + (start.month - 1)) + months
    year = zero_based // 12
    month = (zero_based % 12) + 1
    return date(year, month, 1)


def resolve_date_range(
    date_start: str | None = None,
    date_end: str | None = None,
) -> Tuple[str, str]:
    """Resolve (start, end) for EIA API in YYYY-MM format.

    When both are None, returns last calendar month as start and current month as end
    (first period of current month), so the range includes last month's data.
    When one is None, the other is used and the missing bound defaults to last month
    (start) or current month (end) respectively.

    :param date_start: Optional start period (YYYY-MM). If None, uses last calendar month.
    :param date_end: Optional end period (YYYY-MM). If None, uses current month (first period of current month).
    :returns: (start, end) tuple of strings in YYYY-MM form for EIA API.
    """
    today = date.today()
    current = f"{today.year}-{today.month:02d}"
    # Last calendar month: e.g. if today is 2025-02-27, last_month is 2025-01
    if today.month == 1:
        last_year, last_month = today.year - 1, 12
    else:
        last_year, last_month = today.year, today.month - 1
    default_start = f"{last_year}-{last_month:02d}"
    default_end = current  # first period of current month so last month's data is included

    start = date_start if date_start is not None else default_start
    end = date_end if date_end is not None else default_end
    return (start, end)


def make_run_name(cadence: str, date_start: str | None, date_end: str | None) -> str:
    """Build a Prefect flow-run name in the format ``{start} - {end}: {cadence}``.

    :param cadence: Dataset cadence label (monthly, daily, annual, quarterly,
        or 'backfill' for the multi-dataset parent flow).
    :param date_start: Start period or None.
    :param date_end: End period or None.
    :returns: Human-readable run name. Date range comes first so runs sort
        chronologically in the Prefect UI.
    """
    s = date_start or "latest"
    e = date_end or "latest"
    return f"{s} - {e}: {cadence}"


def monthly_chunks(
    date_start: str,
    date_end: str,
    chunk_months: int = 1,
) -> Iterator[Tuple[str, str]]:
    """Yield contiguous date chunks in YYYY-MM inclusive bounds.

    :param date_start: Required start period (YYYY-MM).
    :param date_end: Required end period (YYYY-MM).
    :param chunk_months: Number of months per chunk; must be >= 1.
    :returns: Iterator of (chunk_start, chunk_end) as YYYY-MM strings.
    """
    if chunk_months < 1:
        raise ValueError("chunk_months must be >= 1")

    start = _parse_period(date_start)
    end = _parse_period(date_end)
    if start > end:
        raise ValueError("date_start must be less than or equal to date_end")

    chunk_start = start
    while chunk_start <= end:
        # Inclusive month windows: +chunk_months then step back by one month.
        chunk_end = _add_months(chunk_start, chunk_months)
        chunk_end = _add_months(chunk_end, -1)
        if chunk_end > end:
            chunk_end = end
        yield (_format_period(chunk_start), _format_period(chunk_end))
        chunk_start = _add_months(chunk_end, 1)
