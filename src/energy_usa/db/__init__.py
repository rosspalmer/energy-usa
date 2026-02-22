"""Database layer for ingest and future read endpoints.

This package provides a sync connection helper and upsert for the EIA retail-sales
ingest table. No ORM; uses psycopg for direct SQL.
"""

from energy_usa.db.retail_sales import get_connection, upsert_retail_sales

__all__ = ["get_connection", "upsert_retail_sales"]
