"""Data source API clients.

Each source (EIA, EPA, FERC) gets its own module. All clients satisfy
the DataClient protocol defined in base.py.
"""

from energy_usa.clients.base import DataClient
from energy_usa.clients.eia import EIAClient, EIAManager

__all__ = ["DataClient", "EIAClient", "EIAManager"]
