"""Unit tests for db/transform/electricity/retail_by_state.py.

Tests use mock psycopg connections so no real database is needed.
They verify:
- ``query_retail_by_state`` returns a list of dicts and issues SQL that
  references the correct source table and uses GROUP BY.
- ``upsert_retail_by_state`` returns 0 for empty input and issues an
  INSERT INTO … ON CONFLICT statement targeting the right transform table.
"""

from unittest.mock import MagicMock

from energy_usa.db.transform.electricity.retail_by_state import (
    _QUERY_SQL,
    _UPSERT_SQL,
    query_retail_by_state,
    upsert_retail_by_state,
)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _mock_conn(fetchall_return=None):
    """Return a mock psycopg connection and its cursor.

    :param fetchall_return: Value returned by ``cursor.fetchall()``.
    """
    conn = MagicMock()
    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    cur.fetchall.return_value = fetchall_return or []
    conn.cursor.return_value = cur
    return conn, cur


# ── query_retail_by_state ─────────────────────────────────────────────────────


def test_query_returns_list_of_dicts():
    sample = [
        {"state": "CA", "period": "2023-03-01", "total_revenue": 5000.0,
         "total_sales": 25000.0, "avg_price": 0.2, "total_customers": 1000},
    ]
    conn, cur = _mock_conn(fetchall_return=sample)
    result = query_retail_by_state(conn)
    assert result == sample
    assert isinstance(result, list)


def test_query_calls_execute_once():
    conn, cur = _mock_conn()
    query_retail_by_state(conn)
    cur.execute.assert_called_once()


def test_query_sql_references_retail_sales():
    assert "eia.retail_sales" in _QUERY_SQL


def test_query_sql_has_group_by():
    assert "GROUP BY" in _QUERY_SQL.upper()


def test_query_sql_excludes_national_totals():
    assert "stateid != 'US'" in _QUERY_SQL


def test_query_sql_aggregates_revenue():
    assert "SUM(revenue)" in _QUERY_SQL


def test_query_sql_aggregates_sales():
    assert "SUM(sales)" in _QUERY_SQL


def test_query_sql_aggregates_customers():
    assert "SUM(customers)" in _QUERY_SQL


def test_query_sql_computes_avg_price():
    assert "avg_price" in _QUERY_SQL


# ── upsert_retail_by_state ────────────────────────────────────────────────────


def test_upsert_empty_input_returns_zero():
    conn, cur = _mock_conn()
    result = upsert_retail_by_state(conn, [])
    assert result == 0
    cur.executemany.assert_not_called()
    conn.commit.assert_not_called()


def test_upsert_returns_row_count():
    conn, cur = _mock_conn()
    rows = [
        {"state": "CA", "period": "2023-03-01", "total_revenue": 5000.0,
         "total_sales": 25000.0, "avg_price": 0.2, "total_customers": 1000},
        {"state": "TX", "period": "2023-03-01", "total_revenue": 8000.0,
         "total_sales": 40000.0, "avg_price": 0.2, "total_customers": 2000},
    ]
    result = upsert_retail_by_state(conn, rows)
    assert result == 2


def test_upsert_calls_executemany_with_rows():
    conn, cur = _mock_conn()
    rows = [
        {"state": "NY", "period": "2022-06-01", "total_revenue": 3000.0,
         "total_sales": 15000.0, "avg_price": 0.2, "total_customers": 500},
    ]
    upsert_retail_by_state(conn, rows)
    cur.executemany.assert_called_once()
    call_args = cur.executemany.call_args
    assert call_args[0][1] == rows


def test_upsert_commits_on_success():
    conn, _ = _mock_conn()
    rows = [{"state": "FL", "period": "2021-01-01", "total_revenue": 1000.0,
             "total_sales": 5000.0, "avg_price": 0.2, "total_customers": 200}]
    upsert_retail_by_state(conn, rows)
    conn.commit.assert_called_once()


def test_upsert_sql_targets_electricity_retail_by_state():
    assert "electricity.retail_by_state" in _UPSERT_SQL


def test_upsert_sql_has_on_conflict():
    assert "ON CONFLICT" in _UPSERT_SQL.upper()


def test_upsert_sql_has_do_update():
    assert "DO UPDATE" in _UPSERT_SQL.upper()
