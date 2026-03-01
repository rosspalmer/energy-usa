"""Date range helper for EIA ingest flows.

EIA API v2 electricity data endpoints accept start and end query parameters.
Format is YYYY-MM for monthly series (e.g. retail-sales, state-electricity-profiles).
When date_start or date_end are omitted, default is last calendar month through
the first period of the current month (end = current month) so the API returns rows.
"""

from datetime import date
from typing import Tuple


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
