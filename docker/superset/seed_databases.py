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
    {
        "name": "Transform",
        "uri": f"{_uri}/transform",
        "description": "Domain models — electricity, fossil fuels, emissions, pricing",
    },
]

# All EIA ingest tables — in the "eia" schema (schema.table format).
# Each entry is (schema, table_name).
DATASETS = [
    ("eia", "retail_sales"),
    ("eia", "electric_power_operational"),
    ("eia", "state_source_disposition"),
    ("eia", "state_summary"),
    ("eia", "dataset_cadence"),
    ("eia", "rto_region_data"),
    ("eia", "rto_fuel_type_data"),
    ("eia", "rto_region_sub_ba_data"),
    ("eia", "rto_interchange_data"),
    ("eia", "rto_daily_region_data"),
    ("eia", "facility_fuel"),
    ("eia", "operating_generator_capacity"),
    ("eia", "sep_emissions"),
    ("eia", "sep_capability"),
    ("eia", "sep_net_metering"),
    ("eia", "coal_aggregate_production"),
    ("eia", "coal_consumption_quality"),
    ("eia", "coal_mine_production"),
    ("eia", "crude_oil_imports"),
    ("eia", "nuclear_outages_us"),
    ("eia", "nuclear_outages_facility"),
    ("eia", "co2_emissions"),
    ("eia", "natural_gas_prices"),
    ("eia", "natural_gas_consumption"),
    ("eia", "natural_gas_production"),
    ("eia", "natural_gas_storage"),
    ("eia", "petroleum_prices"),
    ("eia", "petroleum_supply"),
    ("eia", "total_energy"),
    ("eia", "seds"),
    ("eia", "steo"),
    ("eia", "international"),
    ("eia", "biomass_capacity"),
    ("eia", "biomass_production"),
    ("eia", "aeo"),
    ("eia", "ieo"),
    ("quality", "audit_rules"),
    ("quality", "audit_results"),
]

TRANSFORM_DATASETS = [
    ("electricity", "generation_mix"),
    ("electricity", "retail_by_state"),
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

    # --- Seed transform datasets ---
    transform_db = db.session.query(Database).filter_by(database_name="Transform").first()
    if transform_db:
        for schema, table_name in TRANSFORM_DATASETS:
            existing_dataset = (
                db.session.query(SqlaTable)
                .filter_by(database_id=transform_db.id, schema=schema, table_name=table_name)
                .first()
            )
            if not existing_dataset:
                dataset = SqlaTable(
                    database_id=transform_db.id,
                    schema=schema,
                    table_name=table_name,
                )
                db.session.add(dataset)
                print(f"  Added dataset:    {schema}.{table_name}")
            else:
                print(f"  Already exists:   {schema}.{table_name}")
        db.session.commit()

print("Database and dataset seeding complete.")
