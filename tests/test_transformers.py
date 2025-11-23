import pytest
import pandas as pd
from unittest.mock import patch
from energyusa.models import EIAData, Consumption
from energyusa.transformers.main import transform_eia_data
import os

def test_transform_eia_seds(db_session_commit):
    # Use db_session_commit so data is persisted for the separate pandas connection
    session = db_session_commit
    
    # Seed raw data
    raw_record = EIAData(
        api_path="seds/data",
        period="2020",
        value=500.0,
        raw_json={"period": "2020", "value": 500.0, "unit": "BBTU"}
    )
    session.add(raw_record)
    session.commit()

    # Verify seed data is visible
    from sqlalchemy import create_engine, text
    test_db_url = os.getenv("TEST_DATABASE_URL", "postgresql://user:password@localhost:5432/energyusa_test")
    test_engine = create_engine(test_db_url)
    
    with test_engine.connect() as conn:
        result = conn.execute(text("SELECT count(*) FROM raw.eia_data")).scalar()
        assert result == 1, "Seed data not visible to new connection"

    # Patch the engine used in the transformer
    with patch("energyusa.transformers.main.engine", test_engine):
        transform_eia_data()
        
    session.expire_all()
    
    results = session.query(Consumption).all()
    assert len(results) == 1
    assert results[0].value == 500.0
    assert results[0].unit == "BBTU"
