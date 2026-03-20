"""Unit tests for Dash dashboard helper functions.

Tests _render_data_status_banner and the data-fetching helpers (_get_states,
_get_retail_price, _get_generation) using mocked Django DB connections so no
running database is required.
"""
import sys
from unittest.mock import MagicMock, patch

import django
import pytest


# Minimal Django setup required before importing dash_app (which imports Django)
@pytest.fixture(autouse=True, scope="module")
def django_setup():
    """Configure Django with a minimal in-memory SQLite DB for these tests."""
    from django.conf import settings
    if not settings.configured:
        settings.configure(
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": ":memory:",
                }
            },
            INSTALLED_APPS=[
                "django.contrib.contenttypes",
                "django.contrib.auth",
                "django_plotly_dash",
            ],
            X_FRAME_OPTIONS="SAMEORIGIN",
        )
        django.setup()


@pytest.fixture
def mock_ingest_conn():
    """Patch Django's 'ingest' connection with a mock that returns canned data."""
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    conn = MagicMock()
    conn.cursor.return_value = cursor

    with patch("dashboard.dash_app.connections") as mock_connections:
        mock_connections.__getitem__ = MagicMock(return_value=conn)
        mock_connections.__contains__ = MagicMock(return_value=True)
        yield cursor


# ── _render_data_status_banner ───────────────────────────────────────────────


class TestRenderDataStatusBanner:
    def test_ingest_error_returns_red_banner(self):
        from dashboard.dash_app import _render_data_status_banner

        status = {"ingest_error": "Cannot connect", "tables": {}}
        result = _render_data_status_banner(status)
        # Should return a Div (not empty list)
        assert result is not None
        assert not isinstance(result, list)
        # Red border color in style
        assert "red" in str(result.style.get("borderLeft", "")).lower()

    def test_all_tables_populated_returns_empty(self):
        from dashboard.dash_app import _render_data_status_banner

        status = {
            "ingest_error": None,
            "tables": {
                "eia_retail_sales": 1000,
                "eia_electric_power_operational": 500,
                "eia_state_summary": 200,
            },
        }
        result = _render_data_status_banner(status)
        assert result == []

    def test_empty_table_returns_teal_banner(self):
        from dashboard.dash_app import _render_data_status_banner

        status = {
            "ingest_error": None,
            "tables": {
                "eia_retail_sales": 0,
                "eia_electric_power_operational": 500,
                "eia_state_summary": 200,
            },
        }
        result = _render_data_status_banner(status)
        assert result is not None
        assert not isinstance(result, list)
        assert "teal" in str(result.style.get("borderLeft", "")).lower()

    def test_empty_table_lists_flow_name(self):
        from dashboard.dash_app import _render_data_status_banner

        status = {
            "ingest_error": None,
            "tables": {"eia_retail_sales": 0, "eia_electric_power_operational": 10,
                       "eia_state_summary": 5},
        }
        result = _render_data_status_banner(status)
        # The rendered HTML should mention the flow name
        assert "ingest_eia_retail_sales" in str(result)


# ── chart figure shapes ──────────────────────────────────────────────────────


class TestUpdatePrice:
    def test_no_states_returns_empty_figure(self):
        from dashboard.dash_app import _update_price

        with patch("dashboard.dash_app._get_retail_price", return_value=__import__("pandas").DataFrame()):
            fig = _update_price(None, None)
        assert "no data" in fig.layout.title.text.lower()

    def test_with_state_returns_line_chart(self):
        import pandas as pd
        from datetime import date
        from dashboard.dash_app import _update_price

        df = pd.DataFrame([
            {"period": date(2024, 1, 1), "stateid": "CA", "avg_price": 0.25},
            {"period": date(2024, 2, 1), "stateid": "CA", "avg_price": 0.26},
        ])
        with patch("dashboard.dash_app._get_retail_price", return_value=df):
            fig = _update_price("CA", None)
        # Figure should have data traces
        assert len(fig.data) > 0

    def test_two_states_returns_two_traces(self):
        import pandas as pd
        from datetime import date
        from dashboard.dash_app import _update_price

        df = pd.DataFrame([
            {"period": date(2024, 1, 1), "stateid": "CA", "avg_price": 0.25},
            {"period": date(2024, 1, 1), "stateid": "TX", "avg_price": 0.12},
        ])
        with patch("dashboard.dash_app._get_retail_price", return_value=df):
            fig = _update_price("CA", "TX")
        assert len(fig.data) == 2


class TestUpdateGeneration:
    def test_no_states_returns_empty_figure(self):
        from dashboard.dash_app import _update_generation

        with patch("dashboard.dash_app._get_generation", return_value=__import__("pandas").DataFrame()):
            fig = _update_generation(None, None)
        assert "no data" in fig.layout.title.text.lower()

    def test_with_state_returns_line_chart(self):
        import pandas as pd
        from datetime import date
        from dashboard.dash_app import _update_generation

        df = pd.DataFrame([
            {"period": date(2024, 1, 1), "stateid": "CA", "total_generation": 50000},
        ])
        with patch("dashboard.dash_app._get_generation", return_value=df):
            fig = _update_generation("CA", None)
        assert len(fig.data) > 0


# ── chart styling ─────────────────────────────────────────────────────────────


class TestChartStyling:
    def test_price_chart_uses_gas_station_colors(self):
        """Price chart should use brand teal as primary color."""
        import pandas as pd
        from datetime import date
        from dashboard.dash_app import _update_price, BRAND_COLORS

        df = pd.DataFrame([
            {"period": date(2024, 1, 1), "stateid": "CA", "avg_price": 0.25},
        ])
        with patch("dashboard.dash_app._get_retail_price", return_value=df):
            fig = _update_price("CA", None)
        # The first trace color should match our brand palette
        trace_color = fig.data[0].line.color
        assert trace_color in BRAND_COLORS

    def test_generation_chart_uses_gas_station_colors(self):
        """Generation chart should use brand teal as primary color."""
        import pandas as pd
        from datetime import date
        from dashboard.dash_app import _update_generation, BRAND_COLORS

        df = pd.DataFrame([
            {"period": date(2024, 1, 1), "stateid": "CA", "total_generation": 50000},
        ])
        with patch("dashboard.dash_app._get_generation", return_value=df):
            fig = _update_generation("CA", None)
        trace_color = fig.data[0].line.color
        assert trace_color in BRAND_COLORS
