"""Normalize EIA period values to Postgres DATE (first day of month, quarter, or year)."""

import logging
from datetime import date
from typing import Literal

logger = logging.getLogger(__name__)

Cadence = Literal["monthly", "yearly", "daily", "quarterly"]


def normalize_period(raw: str | None, cadence: Cadence) -> date | None:
    """Convert EIA period string to a date.

    - "monthly"   → first day of month (YYYY-MM or YYYY-MM-DD → date(Y, M, 1))
    - "yearly"    → Jan 1 of year (YYYY → date(Y, 1, 1))
    - "daily"     → exact date (YYYY-MM-DD or YYYY-MM-DDTHH → date(Y, M, D))
    - "quarterly" → first day of quarter (YYYY-QN → date(Y, quarter_start_month, 1))

    :param raw: Period from EIA (e.g. "2024-03", "2024", "2024-Q2", "2024-03-15").
    :param cadence: Expected grain.
    :returns: Normalized date, or None if unparseable (caller should skip row).
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        if cadence == "yearly":
            if len(s) == 4 and s.isdigit():
                return date(int(s), 1, 1)
            if len(s) >= 4 and s[:4].isdigit():
                return date(int(s[:4]), 1, 1)
            return None

        if cadence == "quarterly":
            # Accepts "2024-Q2", "2024Q2"
            upper = s.upper().replace("-", "")
            if "Q" in upper:
                parts = upper.split("Q")
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    year = int(parts[0])
                    quarter = int(parts[1])
                    if 1 <= quarter <= 4:
                        month = (quarter - 1) * 3 + 1
                        return date(year, month, 1)
            # Fallback: treat as yearly or monthly
            return normalize_period(raw, "monthly") or normalize_period(raw, "yearly")

        if cadence == "daily":
            # YYYY-MM-DDTHH... → take date portion only
            date_part = s.split("T")[0]
            parts = date_part.split("-")
            if len(parts) >= 3 and all(p.isdigit() for p in parts[:3]):
                return date(int(parts[0]), int(parts[1]), int(parts[2]))
            # Fallback to monthly
            return normalize_period(raw, "monthly")

        # monthly: YYYY-MM or YYYY-MM-DD → first day of month
        parts = s.split("T")[0].split("-")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            y, m = int(parts[0]), int(parts[1])
            if 1 <= m <= 12:
                return date(y, m, 1)
        if len(s) == 4 and s.isdigit():
            return date(int(s), 1, 1)
        return None
    except (ValueError, TypeError) as e:
        logger.warning("period normalization failed: raw=%r cadence=%s error=%s", raw, cadence, e)
        return None


def safe_numeric(val: object) -> float | None:
    """Coerce an EIA value to float, returning None for non-numeric strings like 'Not Available'."""
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def normalize_period_text(raw: str | None) -> str | None:
    """Return raw period string unchanged (for hourly/sub-hourly data stored as TEXT).

    :param raw: Period string from EIA (e.g. "2024-01-15T05").
    :returns: Stripped string, or None if empty.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    return s if s else None
