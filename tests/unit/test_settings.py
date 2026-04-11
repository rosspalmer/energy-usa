"""Unit tests for Settings configuration.

Tests that Settings loads the ingest_database_url correctly.
"""
import pytest

from energy_usa.config import Settings


def test_ingest_database_url_defaults_to_empty():
    s = Settings(_env_file=None)
    assert s.ingest_database_url == ""


def test_ingest_database_url_can_be_set():
    s = Settings(
        ingest_database_url="postgresql://u:p@h:5432/ingest",
        _env_file=None,
    )
    assert s.ingest_database_url == "postgresql://u:p@h:5432/ingest"
