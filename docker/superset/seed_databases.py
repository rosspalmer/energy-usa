#!/usr/bin/env python3
"""Seed initial database connections and datasets into Superset on first run.

Called by init.sh after superset db upgrade and superset init.
Idempotent — skips any connection or dataset that already exists by name.
"""
import os
import sys

from superset import create_app
from superset.extensions import db

POSTGRES_HOST = os.environ["POSTGRES_HOST"]
POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]

_uri = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432"

CONNECTIONS = [
    {
        "name": "EIA Ingest",
        "uri": f"{_uri}/ingest",
        "description": "EIA API raw data — retail sales, power generation, state summary, source disposition",
    },
]

# All EIA ingest tables — all in the "ingest" schema after schema migration.
# Each entry is (schema, table_name).
DATASETS = [
    ("ingest", "eia_retail_sales"),
    ("ingest", "eia_electric_power_operational"),
    ("ingest", "eia_state_source_disposition"),
    ("ingest", "eia_state_summary"),
    ("ingest", "ingest_dataset_cadence"),
    ("ingest", "eia_rto_region_data"),
    ("ingest", "eia_rto_fuel_type_data"),
    ("ingest", "eia_rto_region_sub_ba_data"),
    ("ingest", "eia_rto_interchange_data"),
    ("ingest", "eia_rto_daily_region_data"),
    ("ingest", "eia_facility_fuel"),
    ("ingest", "eia_operating_generator_capacity"),
    ("ingest", "eia_sep_emissions"),
    ("ingest", "eia_sep_capability"),
    ("ingest", "eia_sep_net_metering"),
    ("ingest", "eia_coal_aggregate_production"),
    ("ingest", "eia_coal_consumption_quality"),
    ("ingest", "eia_coal_mine_production"),
    ("ingest", "eia_crude_oil_imports"),
    ("ingest", "eia_nuclear_outages_us"),
    ("ingest", "eia_nuclear_outages_facility"),
    ("ingest", "eia_co2_emissions"),
    ("ingest", "eia_natural_gas_prices"),
    ("ingest", "eia_natural_gas_consumption"),
    ("ingest", "eia_natural_gas_production"),
    ("ingest", "eia_natural_gas_storage"),
    ("ingest", "eia_petroleum_prices"),
    ("ingest", "eia_petroleum_supply"),
    ("ingest", "eia_total_energy"),
    ("ingest", "eia_seds"),
    ("ingest", "eia_steo"),
    ("ingest", "eia_international"),
    ("ingest", "eia_biomass_capacity"),
    ("ingest", "eia_biomass_production"),
    ("ingest", "eia_aeo"),
    ("ingest", "eia_ieo"),
]

app = create_app()
with app.app_context():
    from superset.models.core import Database
    from superset.connectors.sqla.models import SqlaTable

    # --- Seed database connections ---
    for conn in CONNECTIONS:
        existing = db.session.query(Database).filter_by(database_name=conn["name"]).first()
        if not existing:
            entry = Database(
                database_name=conn["name"],
                sqlalchemy_uri=conn["uri"],
            )
            db.session.add(entry)
            print(f"  Added connection: {conn['name']}")
        else:
            print(f"  Already exists:   {conn['name']}")
    db.session.commit()

    # --- Seed datasets ---
    ingest_db = db.session.query(Database).filter_by(database_name="EIA Ingest").first()
    if not ingest_db:
        print("ERROR: 'EIA Ingest' database connection not found — cannot seed datasets.")
        sys.exit(1)

    for schema, table_name in DATASETS:
        existing_dataset = (
            db.session.query(SqlaTable)
            .filter_by(database_id=ingest_db.id, schema=schema, table_name=table_name)
            .first()
        )
        if not existing_dataset:
            dataset = SqlaTable(
                database_id=ingest_db.id,
                schema=schema,
                table_name=table_name,
            )
            db.session.add(dataset)
            print(f"  Added dataset:    {schema}.{table_name}")
        else:
            print(f"  Already exists:   {schema}.{table_name}")
    db.session.commit()

print("Database and dataset seeding complete.")
