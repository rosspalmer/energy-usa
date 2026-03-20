"""Unit tests for Settings configuration.

Tests that Settings resolves the correct database URL for ingest flows:
ingest_database_url is preferred when set; falls back to database_url otherwise.
"""
import pytest

from energy_usa.config import Settings


def test_ingest_database_url_defaults_to_empty():
    s = Settings(database_url="postgresql://u:p@h:5432/app", _env_file=None)
    assert s.ingest_database_url == ""


def test_ingest_database_url_can_be_set_independently():
    s = Settings(
        database_url="postgresql://u:p@h:5432/app",
        ingest_database_url="postgresql://u:p@h:5432/ingest",
        _env_file=None,
    )
    assert s.ingest_database_url == "postgresql://u:p@h:5432/ingest"


def test_effective_ingest_url_falls_back_to_database_url():
    """When ingest_database_url is unset, effective_ingest_url returns database_url."""
    s = Settings(database_url="postgresql://u:p@h:5432/ingest", _env_file=None)
    assert s.effective_ingest_url == "postgresql://u:p@h:5432/ingest"


def test_effective_ingest_url_prefers_ingest_database_url():
    s = Settings(
        database_url="postgresql://u:p@h:5432/app",
        ingest_database_url="postgresql://u:p@h:5432/ingest",
        _env_file=None,
    )
    assert s.effective_ingest_url == "postgresql://u:p@h:5432/ingest"
