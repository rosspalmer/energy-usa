"""Database layer — connection helpers, period normalization, and ingest upserts.

Subpackages:
- db.ingest.eia — EIA upsert functions (one per dataset)
- db.connection — shared get_connection() helper
- db.period — period normalization utilities
- db.dataframe — SQL-to-DataFrame helper
"""

from energy_usa.db.connection import get_connection
from energy_usa.db.dataframe import query_to_dataframe
from energy_usa.db.ingest.eia import *  # noqa: F401,F403 — re-exports all upsert functions

__all__ = [
    "get_connection",
    "query_to_dataframe",
]
