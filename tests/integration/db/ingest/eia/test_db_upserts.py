"""Integration tests for DB upsert functions against a real Postgres database.

These tests require INGEST_DATABASE_URL to point to a running Postgres with the
ingest schema applied (docker/postgres/init/ingest/*.sql). They are skipped
automatically if the database is not available.
"""
from datetime import date

import pytest

from energy_usa.db.ingest.eia.retail_sales import upsert_retail_sales
from energy_usa.db.ingest.eia.electric_power_operational import upsert_electric_power_operational
from energy_usa.db.ingest.eia.state_summary import upsert_state_summary

from tests.integration.conftest import skip_if_no_db


# ── eia_retail_sales ─────────────────────────────────────────────────────────


@skip_if_no_db
@pytest.mark.integration
def test_retail_sales_upsert_inserts_row(ingest_conn):
    rows = [{
        "period": "2024-01",
        "stateid": "TEST_CA",
        "sectorid": "RES",
        "revenue": 100.0,
        "sales": 200.0,
        "price": 0.15,
        "customers": 50,
    }]
    count = upsert_retail_sales(ingest_conn, rows)
    assert count == 1

    with ingest_conn.cursor() as cur:
        cur.execute(
            "SELECT price FROM eia.retail_sales WHERE stateid = 'TEST_CA' AND period = '2024-01-01'"
        )
        row = cur.fetchone()
    assert row is not None
    assert float(row["price"]) == pytest.approx(0.15)


@skip_if_no_db
@pytest.mark.integration
def test_retail_sales_upsert_is_idempotent(ingest_conn):
    rows = [{
        "period": "2024-02",
        "stateid": "TEST_TX",
        "sectorid": "COM",
        "revenue": 50.0,
        "sales": 100.0,
        "price": 0.10,
        "customers": 25,
    }]
    upsert_retail_sales(ingest_conn, rows)
    # Update price and upsert again
    rows[0]["price"] = 0.12
    upsert_retail_sales(ingest_conn, rows)

    with ingest_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*), MAX(price) FROM eia.retail_sales "
            "WHERE stateid = 'TEST_TX' AND period = '2024-02-01' AND sectorid = 'COM'"
        )
        result = cur.fetchone()
    assert result[0] == 1  # only one row (upserted, not duplicated)
    assert float(result[1]) == pytest.approx(0.12)


# ── eia_electric_power_operational ───────────────────────────────────────────


@skip_if_no_db
@pytest.mark.integration
def test_electric_power_upsert_inserts_row(ingest_conn):
    rows = [{
        "period": "2024-01",
        "stateid": "TEST_NY",
        "sectorid": "ALL",
        "fueltypeid": "SUN",
        "generation": 5000.0,
    }]
    count = upsert_electric_power_operational(ingest_conn, rows)
    assert count == 1

    with ingest_conn.cursor() as cur:
        cur.execute(
            "SELECT generation FROM eia.electric_power_operational "
            "WHERE stateid = 'TEST_NY' AND fueltypeid = 'SUN' AND period = '2024-01-01'"
        )
        row = cur.fetchone()
    assert row is not None
    assert float(row["generation"]) == pytest.approx(5000.0)


@skip_if_no_db
@pytest.mark.integration
def test_electric_power_skips_all_state_in_db(ingest_conn):
    rows = [{
        "period": "2024-01",
        "stateid": "ALL",
        "sectorid": "ALL",
        "fueltypeid": "NG",
        "generation": 99999.0,
    }]
    count = upsert_electric_power_operational(ingest_conn, rows)
    assert count == 0


@skip_if_no_db
@pytest.mark.integration
def test_electric_power_zero_generation_stored(ingest_conn):
    rows = [{
        "period": "2024-03",
        "stateid": "TEST_VT",
        "sectorid": "ALL",
        "fueltypeid": "COL",
        "generation": 0,
    }]
    upsert_electric_power_operational(ingest_conn, rows)

    with ingest_conn.cursor() as cur:
        cur.execute(
            "SELECT generation FROM eia.electric_power_operational "
            "WHERE stateid = 'TEST_VT' AND fueltypeid = 'COL' AND period = '2024-03-01'"
        )
        row = cur.fetchone()
    # generation = 0 must be stored as 0, not NULL
    assert row is not None
    assert row["generation"] == 0


# ── eia_state_summary ────────────────────────────────────────────────────────


@skip_if_no_db
@pytest.mark.integration
def test_state_summary_upsert_inserts_row(ingest_conn):
    rows = [{
        "period": "2023",
        "stateid": "TEST_WA",
        "average-retail-price": 10.5,
        "total-generation": 150000,
        "total-consumption": 140000,
    }]
    count = upsert_state_summary(ingest_conn, rows)
    assert count == 1

    with ingest_conn.cursor() as cur:
        cur.execute(
            "SELECT average_retail_price, total_generation FROM eia.state_summary "
            "WHERE stateid = 'TEST_WA' AND period = '2023-01-01'"
        )
        row = cur.fetchone()
    assert row is not None
    assert float(row["average_retail_price"]) == pytest.approx(10.5)
    assert float(row["total_generation"]) == pytest.approx(150000)


@skip_if_no_db
@pytest.mark.integration
def test_state_summary_upsert_is_idempotent(ingest_conn):
    rows = [{
        "period": "2022",
        "stateid": "TEST_OR",
        "average-retail-price": 9.0,
        "total-generation": 80000,
        "total-consumption": 75000,
    }]
    upsert_state_summary(ingest_conn, rows)
    rows[0]["average-retail-price"] = 9.5
    upsert_state_summary(ingest_conn, rows)

    with ingest_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*), MAX(average_retail_price) FROM eia.state_summary "
            "WHERE stateid = 'TEST_OR' AND period = '2022-01-01'"
        )
        result = cur.fetchone()
    assert result[0] == 1
    assert float(result[1]) == pytest.approx(9.5)
