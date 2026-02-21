"""EIA API client and call manager.

Public interface for talking to the U.S. Energy Information Administration
API v2: use :class:`EIAClient` for low-level requests, or :class:`EIAManager`
for production use (concurrency limit, retries, timeouts). FastAPI endpoints
should depend on the manager, which is created at startup and stored in app state.
"""

from energy_usa.eia.client import EIAClient
from energy_usa.eia.manager import EIAManager

__all__ = ["EIAClient", "EIAManager"]
