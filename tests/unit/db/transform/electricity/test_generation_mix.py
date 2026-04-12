"""Unit tests for db/transform/electricity/generation_mix.py.

Tests use mock psycopg connections so no real database is needed.
They verify:
- ``query_generation_mix`` returns a list of dicts and issues SQL that
  references the correct source tables and uses JOIN / GROUP BY.
- ``upsert_generation_mix`` returns 0 for empty input and issues an
  INSERT INTO … ON CONFLICT statement targeting the right transform table.
"""

from unittest.mock import MagicMock

from energy_usa.db.transform.electricity.generation_mix import (
    _QUERY_SQL,
    _UPSERT_SQL,
    query_generation_mix,
    upsert_generation_mix,
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


# ── query_generation_mix ───────────────────────────────────────────────────────


def test_query_returns_list_of_dicts():
    sample = [
        {"state": "CA", "period": "2023-01-01", "total_generation_mwh": 100,
         "co2_tons": 50.0, "carbon_intensity": 0.5},
    ]
    conn, cur = _mock_conn(fetchall_return=sample)
    result = query_generation_mix(conn)
    assert result == sample
    assert isinstance(result, list)


def test_query_calls_execute_once():
    conn, cur = _mock_conn()
    query_generation_mix(conn)
    cur.execute.assert_called_once()


def test_query_sql_references_state_source_disposition():
    assert "eia.state_source_disposition" in _QUERY_SQL


def test_query_sql_references_co2_emissions():
    assert "eia.co2_emissions" in _QUERY_SQL


def test_query_sql_has_join():
    assert "JOIN" in _QUERY_SQL.upper()


def test_query_sql_has_group_by():
    assert "GROUP BY" in _QUERY_SQL.upper()


def test_query_sql_excludes_national_totals():
    assert "stateid != 'US'" in _QUERY_SQL


def test_query_sql_filters_co2_by_total_fuel_and_electric_sector():
    assert "fuel_id = 'TO'" in _QUERY_SQL
    assert "sector_id = 'EC'" in _QUERY_SQL


def test_query_sql_computes_carbon_intensity():
    assert "carbon_intensity" in _QUERY_SQL


# ── upsert_generation_mix ─────────────────────────────────────────────────────


def test_upsert_empty_input_returns_zero():
    conn, cur = _mock_conn()
    result = upsert_generation_mix(conn, [])
    assert result == 0
    cur.executemany.assert_not_called()
    conn.commit.assert_not_called()


def test_upsert_returns_row_count():
    conn, cur = _mock_conn()
    rows = [
        {"state": "CA", "period": "2023-01-01", "total_generation_mwh": 100,
         "co2_tons": 50.0, "carbon_intensity": 0.5},
        {"state": "TX", "period": "2023-01-01", "total_generation_mwh": 200,
         "co2_tons": 120.0, "carbon_intensity": 0.6},
    ]
    result = upsert_generation_mix(conn, rows)
    assert result == 2


def test_upsert_calls_executemany_with_rows():
    conn, cur = _mock_conn()
    rows = [
        {"state": "NY", "period": "2022-06-01", "total_generation_mwh": 50,
         "co2_tons": 20.0, "carbon_intensity": 0.4},
    ]
    upsert_generation_mix(conn, rows)
    cur.executemany.assert_called_once()
    call_args = cur.executemany.call_args
    assert call_args[0][1] == rows


def test_upsert_commits_on_success():
    conn, _ = _mock_conn()
    rows = [{"state": "FL", "period": "2021-01-01", "total_generation_mwh": 80,
             "co2_tons": 40.0, "carbon_intensity": 0.5}]
    upsert_generation_mix(conn, rows)
    conn.commit.assert_called_once()


def test_upsert_sql_targets_electricity_generation_mix():
    assert "electricity.generation_mix" in _UPSERT_SQL


def test_upsert_sql_has_on_conflict():
    assert "ON CONFLICT" in _UPSERT_SQL.upper()


def test_upsert_sql_has_do_update():
    assert "DO UPDATE" in _UPSERT_SQL.upper()
