"""Application configuration loaded from environment variables.

This module defines all configurable settings for the Energy USA API,
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

    eia_max_concurrent_requests: int = 4
    """Maximum number of EIA API requests allowed in flight at once (semaphore limit)."""

    eia_max_retries: int = 3
    """Number of retry attempts for failed EIA requests (5xx, timeouts, connection errors)."""
