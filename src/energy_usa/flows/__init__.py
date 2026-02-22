"""Prefect flows for scheduled ingest jobs."""

from energy_usa.flows.eia_retail_sales import ingest_eia_retail_sales

__all__ = ["ingest_eia_retail_sales"]
