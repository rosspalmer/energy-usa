"""Shared pytest configuration and fixtures."""
import os

# Provide minimal Django settings env var so pytest-django can configure Django
# even when DJANGO_SETTINGS_MODULE is set via pyproject.toml.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
