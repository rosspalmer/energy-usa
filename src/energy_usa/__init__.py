"""Energy USA: Live and historical US energy data.

This package provides Prefect flows that ingest data from the U.S. Energy
Information Administration (EIA) API v2 into Postgres, plus a DB layer for
upserts. EIA client and config are used by the Prefect worker. The web app
is Django with Dash (see the web/ project when present).
"""
