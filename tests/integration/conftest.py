"""Fixtures for integration tests that require a real Postgres database.

Integration tests are skipped automatically if INGEST_DATABASE_URL is not set
or the database is unreachable. Mark them with @pytest.mark.integration.
"""
import os

import pytest
import psycopg


INGEST_DATABASE_URL = os.environ.get(
    "INGEST_DATABASE_URL",
    "postgresql://energy:energy@localhost:5432/ingest",
)


def _db_available() -> bool:
    try:
        conn = psycopg.connect(INGEST_DATABASE_URL, connect_timeout=3)
        conn.close()
        return True
    except Exception:
        return False


skip_if_no_db = pytest.mark.skipif(
    not _db_available(),
    reason="Integration tests require a running Postgres at INGEST_DATABASE_URL",
)


@pytest.fixture(scope="function")
def ingest_conn():
    """Open a real psycopg connection for the duration of a test, then rollback."""
    conn = psycopg.connect(INGEST_DATABASE_URL)
    conn.autocommit = False
    yield conn
    conn.rollback()
    conn.close()
