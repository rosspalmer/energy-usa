from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, MetaData, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import CreateSchema

Base = declarative_base()

# Schemas
metadata_raw = MetaData(schema="raw")
metadata_analysis = MetaData(schema="analysis")

# Raw Schema Models

class EIAData(Base):
    __tablename__ = "eia_data"
    __table_args__ = ({"schema": "raw"})  # Removed UniqueConstraint for MVP flexibility

    id = Column(Integer, primary_key=True, index=True)
    api_path = Column(String, index=True)
    period = Column(String, index=True)
    value = Column(Float)
    raw_json = Column(JSON)

class NRELData(Base):
    __tablename__ = "nrel_data"
    __table_args__ = (UniqueConstraint('endpoint', name='uix_nrel_data_endpoint'), {"schema": "raw"})

    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String, index=True)
    raw_json = Column(JSON)

class FERCData(Base):
    __tablename__ = "ferc_data"
    __table_args__ = ({"schema": "raw"}) # Removed UniqueConstraint

    id = Column(Integer, primary_key=True, index=True)
    report_year = Column(Integer, index=True)
    raw_json = Column(JSON)

class EPAData(Base):
    __tablename__ = "epa_data"
    __table_args__ = ({"schema": "raw"}) # Removed UniqueConstraint

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, index=True)
    raw_json = Column(JSON)

# Analysis Schema Models

class Production(Base):
    __tablename__ = "production"
    __table_args__ = ({"schema": "analysis"}) # Removed UniqueConstraint

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    source = Column(String) # EIA, eGRID
    fuel_type = Column(String)
    value = Column(Float)
    unit = Column(String)
    state = Column(String, nullable=True)

class Consumption(Base):
    __tablename__ = "consumption"
    __table_args__ = ({"schema": "analysis"}) # Removed UniqueConstraint

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    sector = Column(String)
    value = Column(Float)
    unit = Column(String)

class Transmission(Base):
    __tablename__ = "transmission"
    __table_args__ = (UniqueConstraint('timestamp', 'balancing_authority', name='uix_transmission_record'), {"schema": "analysis"})

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, index=True)
    balancing_authority = Column(String)
    interchange_value = Column(Float)

class Growth(Base):
    __tablename__ = "growth"
    __table_args__ = (UniqueConstraint('year', 'metric', name='uix_growth_record'), {"schema": "analysis"})

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, index=True)
    metric = Column(String)
    value = Column(Float)

class Maintenance(Base):
    __tablename__ = "maintenance"
    __table_args__ = (UniqueConstraint('asset_id', 'status', name='uix_maintenance_record'), {"schema": "analysis"})

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(String, index=True)
    status = Column(String)
    efficiency_metric = Column(Float, nullable=True)

