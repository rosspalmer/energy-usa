"""Unit tests for upsert normalization logic (no DB required).

Tests verify that each upsert function normalizes EIA API row dicts correctly:
key remapping (hyphenated → snake_case), period normalization, state filtering,
and handling of missing or None values. A mock connection captures what would
be inserted so tests don't need a real Postgres.
"""
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from energy_usa.db.ingest.eia.retail_sales import upsert_retail_sales
from energy_usa.db.ingest.eia.electric_power_operational import upsert_electric_power_operational
from energy_usa.db.ingest.eia.state_summary import upsert_state_summary


# ── Helpers ──────────────────────────────────────────────────────────────────


def _mock_conn():
    """Return a mock psycopg connection that captures executemany calls."""
    conn = MagicMock()
    cursor_ctx = MagicMock()
    cursor_ctx.__enter__ = MagicMock(return_value=cursor_ctx)
    cursor_ctx.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cursor_ctx
    return conn, cursor_ctx


# ── retail_sales ─────────────────────────────────────────────────────────────


def test_retail_sales_empty_input_returns_zero():
    conn, _ = _mock_conn()
    result = upsert_retail_sales(conn, [])
    assert result == 0
    conn.cursor.assert_not_called()


def test_retail_sales_normalizes_period():
    conn, cur = _mock_conn()
    rows = [{"period": "2024-03", "stateid": "CA", "sectorid": "RES",
             "revenue": 100, "sales": 200, "price": 0.15, "customers": 50}]
    upsert_retail_sales(conn, rows)
    call_args = cur.executemany.call_args
    inserted = call_args[0][1]
    assert inserted[0]["period"] == date(2024, 3, 1)


def test_retail_sales_skips_rows_with_invalid_period():
    conn, cur = _mock_conn()
    rows = [{"period": "bad-period", "stateid": "CA", "sectorid": "RES",
             "revenue": 100, "sales": 200, "price": 0.15, "customers": 50}]
    result = upsert_retail_sales(conn, rows)
    assert result == 0


def test_retail_sales_missing_numeric_fields_are_null():
    conn, cur = _mock_conn()
    rows = [{"period": "2024-01", "stateid": "TX", "sectorid": "COM"}]
    upsert_retail_sales(conn, rows)
    call_args = cur.executemany.call_args
    inserted = call_args[0][1]
    row = inserted[0]
    assert row["revenue"] is None
    assert row["sales"] is None
    assert row["price"] is None
    assert row["customers"] is None


def test_retail_sales_returns_row_count():
    conn, _ = _mock_conn()
    rows = [
        {"period": "2024-01", "stateid": "CA", "sectorid": "RES",
         "revenue": 1, "sales": 2, "price": 3, "customers": 4},
        {"period": "2024-02", "stateid": "TX", "sectorid": "RES",
         "revenue": 1, "sales": 2, "price": 3, "customers": 4},
    ]
    result = upsert_retail_sales(conn, rows)
    assert result == 2


# ── electric_power_operational ───────────────────────────────────────────────


def test_electric_power_skips_empty_input():
    conn, _ = _mock_conn()
    result = upsert_electric_power_operational(conn, [])
    assert result == 0


def test_electric_power_skips_national_all_rows():
    conn, _ = _mock_conn()
    rows = [{"period": "2024-01", "stateid": "ALL", "sectorid": "ALL",
             "fueltypeid": "NG", "generation": 100}]
    result = upsert_electric_power_operational(conn, rows)
    assert result == 0


def test_electric_power_skips_null_stateid():
    conn, _ = _mock_conn()
    rows = [{"period": "2024-01", "stateid": None, "sectorid": "ALL",
             "fueltypeid": "NG", "generation": 100}]
    result = upsert_electric_power_operational(conn, rows)
    assert result == 0


def test_electric_power_skips_missing_stateid():
    conn, _ = _mock_conn()
    rows = [{"period": "2024-01", "sectorid": "ALL",
             "fueltypeid": "NG", "generation": 100}]
    result = upsert_electric_power_operational(conn, rows)
    assert result == 0


def test_electric_power_normalizes_period():
    conn, cur = _mock_conn()
    rows = [{"period": "2024-06", "stateid": "CA", "sectorid": "ALL",
             "fueltypeid": "SUN", "generation": 5000}]
    upsert_electric_power_operational(conn, rows)
    call_args = cur.executemany.call_args
    inserted = call_args[0][1]
    assert inserted[0]["period"] == date(2024, 6, 1)


def test_electric_power_accepts_state_code():
    conn, cur = _mock_conn()
    rows = [{"period": "2024-01", "stateid": "TX", "sectorid": "ALL",
             "fueltypeid": "NG", "generation": 12345}]
    count = upsert_electric_power_operational(conn, rows)
    assert count == 1


def test_electric_power_preserves_zero_generation():
    """generation=0 must be stored as 0, not dropped as falsy."""
    conn, cur = _mock_conn()
    rows = [{"period": "2024-01", "stateid": "VT", "sectorid": "ALL",
             "fueltypeid": "COL", "generation": 0}]
    upsert_electric_power_operational(conn, rows)
    call_args = cur.executemany.call_args
    inserted = call_args[0][1]
    # generation should be 0, not None
    assert inserted[0]["generation"] == 0


def test_electric_power_skips_row_missing_required_fields():
    conn, _ = _mock_conn()
    # Missing fueltypeid
    rows = [{"period": "2024-01", "stateid": "CA", "sectorid": "ALL", "generation": 100}]
    result = upsert_electric_power_operational(conn, rows)
    assert result == 0


# ── state_summary ─────────────────────────────────────────────────────────────


def test_state_summary_empty_input():
    conn, _ = _mock_conn()
    result = upsert_state_summary(conn, [])
    assert result == 0


def test_state_summary_maps_hyphenated_keys():
    """EIA returns 'average-retail-price', 'total-generation', 'total-consumption'."""
    conn, cur = _mock_conn()
    rows = [{
        "period": "2023",
        "stateid": "CA",
        "average-retail-price": 18.5,
        "total-generation": 200000,
        "total-consumption": 180000,
    }]
    upsert_state_summary(conn, rows)
    call_args = cur.executemany.call_args
    inserted = call_args[0][1]
    row = inserted[0]
    assert row["average_retail_price"] == 18.5
    assert row["total_generation"] == 200000
    assert row["total_consumption"] == 180000


def test_state_summary_yearly_period_normalization():
    conn, cur = _mock_conn()
    rows = [{"period": "2023", "stateid": "TX",
             "average-retail-price": 10.0, "total-generation": 1, "total-consumption": 1}]
    upsert_state_summary(conn, rows)
    call_args = cur.executemany.call_args
    inserted = call_args[0][1]
    assert inserted[0]["period"] == date(2023, 1, 1)


def test_state_summary_skips_missing_stateid():
    conn, _ = _mock_conn()
    rows = [{"period": "2023", "average-retail-price": 10.0}]
    result = upsert_state_summary(conn, rows)
    assert result == 0


def test_state_summary_skips_invalid_period():
    conn, _ = _mock_conn()
    rows = [{"period": "bad", "stateid": "CA", "average-retail-price": 10.0}]
    result = upsert_state_summary(conn, rows)
    assert result == 0


def test_state_summary_accepts_snake_case_keys():
    """Also accepts snake_case variants for the data columns."""
    conn, cur = _mock_conn()
    rows = [{
        "period": "2022",
        "stateid": "NY",
        "average_retail_price": 20.0,
        "total_generation": 100000,
        "total_consumption": 90000,
    }]
    upsert_state_summary(conn, rows)
    call_args = cur.executemany.call_args
    inserted = call_args[0][1]
    row = inserted[0]
    assert row["average_retail_price"] == 20.0


def test_state_summary_null_values_for_missing_data_columns():
    conn, cur = _mock_conn()
    rows = [{"period": "2023", "stateid": "WY"}]
    upsert_state_summary(conn, rows)
    call_args = cur.executemany.call_args
    inserted = call_args[0][1]
    row = inserted[0]
    assert row["average_retail_price"] is None
    assert row["total_generation"] is None
    assert row["total_consumption"] is None
