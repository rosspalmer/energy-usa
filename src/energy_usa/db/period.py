"""Normalize EIA period values to Postgres DATE (first day of month or year)."""

import logging
from datetime import date
from typing import Literal

logger = logging.getLogger(__name__)

Cadence = Literal["monthly", "yearly"]


def normalize_period(raw: str | None, cadence: Cadence) -> date | None:
    """Convert EIA period string to a date (first day of month or year).

    :param raw: Period from EIA (e.g. "2024-03", "2024", "2024-03-15").
    :param cadence: Expected grain: "monthly" -> first day of month, "yearly" -> Jan 1.
    :returns: Normalized date, or None if unparseable (caller should skip row and log).
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
        # monthly: YYYY-MM or YYYY-MM-DD -> first day of month
        parts = s.split("-")
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
