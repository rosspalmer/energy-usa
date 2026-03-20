"""Unit tests for normalize_period.

Tests the period normalization function that converts EIA API period strings
(YYYY-MM, YYYY, YYYY-MM-DD) into Python date objects (first of month/year).
"""
from datetime import date

import pytest

from energy_usa.db.period import normalize_period


# ── Monthly cadence ──────────────────────────────────────────────────────────


def test_monthly_standard_yyyy_mm():
    assert normalize_period("2024-03", "monthly") == date(2024, 3, 1)


def test_monthly_january():
    assert normalize_period("2024-01", "monthly") == date(2024, 1, 1)


def test_monthly_december():
    assert normalize_period("2024-12", "monthly") == date(2024, 12, 1)


def test_monthly_strips_day_component():
    assert normalize_period("2024-03-15", "monthly") == date(2024, 3, 1)


def test_monthly_strips_day_first_of_month():
    assert normalize_period("2024-06-01", "monthly") == date(2024, 6, 1)


def test_monthly_year_only_treated_as_jan():
    assert normalize_period("2024", "monthly") == date(2024, 1, 1)


def test_monthly_none_returns_none():
    assert normalize_period(None, "monthly") is None


def test_monthly_empty_string_returns_none():
    assert normalize_period("", "monthly") is None


def test_monthly_whitespace_only_returns_none():
    assert normalize_period("   ", "monthly") is None


def test_monthly_invalid_string_returns_none():
    assert normalize_period("not-a-date", "monthly") is None


def test_monthly_invalid_month_13():
    assert normalize_period("2024-13", "monthly") is None


def test_monthly_invalid_month_00():
    assert normalize_period("2024-00", "monthly") is None


def test_monthly_non_numeric_returns_none():
    assert normalize_period("XXXX-YY", "monthly") is None


# ── Yearly cadence ───────────────────────────────────────────────────────────


def test_yearly_standard_yyyy():
    assert normalize_period("2024", "yearly") == date(2024, 1, 1)


def test_yearly_early_year():
    assert normalize_period("2000", "yearly") == date(2000, 1, 1)


def test_yearly_with_month_strips_month():
    assert normalize_period("2024-06", "yearly") == date(2024, 1, 1)


def test_yearly_none_returns_none():
    assert normalize_period(None, "yearly") is None


def test_yearly_empty_returns_none():
    assert normalize_period("", "yearly") is None


def test_yearly_invalid_returns_none():
    assert normalize_period("bad", "yearly") is None


def test_yearly_partial_digits():
    # "202" is not a 4-digit year; should return None
    assert normalize_period("202", "yearly") is None
