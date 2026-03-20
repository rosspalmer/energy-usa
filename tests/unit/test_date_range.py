"""Unit tests for date range helpers used by EIA ingest flows.

Tests resolve_date_range (YYYY-MM defaults) and monthly_chunks (iterator over
contiguous month windows). Uses freezegun-style patching of date.today() to
avoid time-dependent assertions.
"""
from datetime import date
from unittest.mock import patch

import pytest

from energy_usa.flows.date_range import monthly_chunks, resolve_date_range


# ── resolve_date_range ───────────────────────────────────────────────────────


def test_both_provided_passes_through():
    start, end = resolve_date_range("2024-01", "2024-12")
    assert start == "2024-01"
    assert end == "2024-12"


def test_both_none_defaults_to_last_and_current_month():
    with patch("energy_usa.flows.date_range.date") as mock_date:
        mock_date.today.return_value = date(2024, 3, 15)
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
        start, end = resolve_date_range()
    assert start == "2024-02"
    assert end == "2024-03"


def test_start_none_defaults_to_last_month():
    with patch("energy_usa.flows.date_range.date") as mock_date:
        mock_date.today.return_value = date(2024, 6, 1)
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
        start, end = resolve_date_range(date_end="2024-06")
    assert start == "2024-05"
    assert end == "2024-06"


def test_end_none_defaults_to_current_month():
    with patch("energy_usa.flows.date_range.date") as mock_date:
        mock_date.today.return_value = date(2024, 6, 1)
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
        start, end = resolve_date_range(date_start="2024-01")
    assert start == "2024-01"
    assert end == "2024-06"


def test_january_default_wraps_to_december():
    """When today is January, last month should be December of the prior year."""
    with patch("energy_usa.flows.date_range.date") as mock_date:
        mock_date.today.return_value = date(2024, 1, 15)
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
        start, end = resolve_date_range()
    assert start == "2023-12"
    assert end == "2024-01"


# ── monthly_chunks ───────────────────────────────────────────────────────────


def test_single_month_yields_one_chunk():
    chunks = list(monthly_chunks("2024-01", "2024-01"))
    assert chunks == [("2024-01", "2024-01")]


def test_three_months_chunk_one_yields_three_chunks():
    chunks = list(monthly_chunks("2024-01", "2024-03"))
    assert chunks == [
        ("2024-01", "2024-01"),
        ("2024-02", "2024-02"),
        ("2024-03", "2024-03"),
    ]


def test_chunk_two_even_split():
    chunks = list(monthly_chunks("2024-01", "2024-04", chunk_months=2))
    assert chunks == [("2024-01", "2024-02"), ("2024-03", "2024-04")]


def test_chunk_two_odd_remainder():
    chunks = list(monthly_chunks("2024-01", "2024-03", chunk_months=2))
    assert chunks == [("2024-01", "2024-02"), ("2024-03", "2024-03")]


def test_chunk_across_year_boundary():
    chunks = list(monthly_chunks("2023-11", "2024-02"))
    assert chunks == [
        ("2023-11", "2023-11"),
        ("2023-12", "2023-12"),
        ("2024-01", "2024-01"),
        ("2024-02", "2024-02"),
    ]


def test_chunk_six_months_single_chunk():
    chunks = list(monthly_chunks("2024-01", "2024-06", chunk_months=6))
    assert chunks == [("2024-01", "2024-06")]


def test_start_greater_than_end_raises():
    with pytest.raises(ValueError, match="date_start"):
        list(monthly_chunks("2024-06", "2024-01"))


def test_zero_chunk_months_raises():
    with pytest.raises(ValueError, match="chunk_months"):
        list(monthly_chunks("2024-01", "2024-03", chunk_months=0))


def test_negative_chunk_months_raises():
    with pytest.raises(ValueError, match="chunk_months"):
        list(monthly_chunks("2024-01", "2024-03", chunk_months=-1))


def test_chunks_are_contiguous_no_gaps():
    """End of one chunk + 1 month == start of next chunk."""
    chunks = list(monthly_chunks("2023-01", "2024-12", chunk_months=3))
    for i in range(len(chunks) - 1):
        _, prev_end = chunks[i]
        next_start, _ = chunks[i + 1]
        prev_y, prev_m = map(int, prev_end.split("-"))
        next_y, next_m = map(int, next_start.split("-"))
        # next month of prev_end should equal next_start
        if prev_m == 12:
            assert next_y == prev_y + 1 and next_m == 1
        else:
            assert next_y == prev_y and next_m == prev_m + 1
