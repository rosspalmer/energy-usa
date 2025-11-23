import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateSchema
from energyusa.models import Base
import os

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql://user:password@localhost:5432/energyusa_test")

@pytest.fixture(scope="session")
def engine():
    return create_engine(TEST_DATABASE_URL)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db(engine):
    """
    Initialize schemas and tables in the test database once per session.
    """
    Base.metadata.drop_all(engine)
    
    inspector = inspect(engine)
    existing_schemas = inspector.get_schema_names()
    
    with engine.connect() as conn:
        if "raw" not in existing_schemas:
            conn.execute(CreateSchema("raw"))
        if "analysis" not in existing_schemas:
            conn.execute(CreateSchema("analysis"))
        conn.commit()

    Base.metadata.create_all(engine)
    yield
    # Base.metadata.drop_all(engine)

@pytest.fixture(scope="function")
def db_session(engine):
    """
    Standard test session with transaction rollback.
    Useful for unit tests that don't need external visibility.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def db_session_commit(engine):
    """
    Session that commits changes. Use for tests involving separate connections (like pandas read_sql).
    Requires manual cleanup or use of 'clean_tables' fixture.
    """
    connection = engine.connect()
    session = sessionmaker(bind=connection)()
    
    yield session
    
    session.close()
    connection.close()

@pytest.fixture(scope="function", autouse=True)
def clean_tables(engine):
    """
    Truncate tables after each test to ensure clean state, 
    especially when using db_session_commit.
    """
    yield
    
    # Truncate all tables in 'raw' and 'analysis' schemas
    # We use CASCADE to handle foreign keys if any
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE raw.eia_data, raw.nrel_data, raw.ferc_data, raw.epa_data CASCADE"))
        conn.execute(text("TRUNCATE TABLE analysis.production, analysis.consumption, analysis.transmission, analysis.growth, analysis.maintenance CASCADE"))
        conn.commit()
