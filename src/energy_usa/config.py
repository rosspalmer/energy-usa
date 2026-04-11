"""Application configuration loaded from environment variables.

This module defines all configurable settings for the Energy USA ingest pipeline,
including EIA API connection details and limits for the API call manager.
Values are read from the process environment and optionally from a ``.env``
file in the project root.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for the Energy USA application and EIA API access.

    All fields can be set via environment variables (same name, uppercase).
    A ``.env`` file in the working directory is loaded automatically if present.
    Register for a free API key at https://www.eia.gov/opendata/register.php
    and set ``EIA_API_KEY``; without it, EIA data endpoints will return 403.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    eia_base_url: str = "https://api.eia.gov/v2"
    """Base URL for EIA API v2. Override for testing or a different environment."""

    eia_api_key: str = ""
    """API key from EIA Open Data registration. Required for all EIA data requests."""

    eia_request_timeout_seconds: float = 30.0
    """Timeout in seconds for each HTTP request to the EIA API."""

    eia_ingest_timeout_seconds: float = 180.0
    """Timeout in seconds for EIA requests during long-running ingest flows (paginated fetches).
    Large pages (e.g. electric-power-operational at high offset) may need 2–3 minutes."""

    eia_page_delay_seconds: float = 0.5
    """Delay in seconds between pagination requests during EIA ingest. Reduces timeouts and respects informal rate limits."""

    eia_max_concurrent_requests: int = 4
    """Maximum number of EIA API requests allowed in flight at once (semaphore limit)."""

    eia_max_retries: int = 5
    """Number of retry attempts for failed EIA requests (5xx, timeouts, connection errors)."""

    ingest_database_url: str = ""
    """PostgreSQL connection URL for the EIA ingest database.
    Example: postgresql://user:password@host:5432/ingest. Empty means ingest features are disabled."""

    transform_database_url: str = ""
    """PostgreSQL connection URL for the transform database.
    Example: postgresql://user:password@host:5432/transform. Empty means transform features are disabled."""
