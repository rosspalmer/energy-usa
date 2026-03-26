#!/usr/bin/env python3
"""Seed initial database connections into Superset on first run.

Called by init.sh after superset db upgrade and superset init.
Idempotent — skips any connection that already exists by name.
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
        "name": "Energy USA App",
        "uri": f"{_uri}/energy_usa",
        "description": "Django application database — sessions, auth",
    },
]

app = create_app()
with app.app_context():
    from superset.models.core import Database
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

print("Database seeding complete.")
