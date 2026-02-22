"""Database layer for ingest and future read endpoints.

This package provides a sync connection helper and upserts for EIA ingest tables.
No ORM; uses psycopg for direct SQL.
"""

from energy_usa.db.electric_power_operational import upsert_electric_power_operational
from energy_usa.db.retail_sales import get_connection, upsert_retail_sales
from energy_usa.db.state_source_disposition import upsert_state_source_disposition
from energy_usa.db.state_summary import upsert_state_summary

__all__ = [
    "get_connection",
    "upsert_retail_sales",
    "upsert_electric_power_operational",
    "upsert_state_source_disposition",
    "upsert_state_summary",
]
