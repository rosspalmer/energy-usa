from sqlalchemy import Column, Integer, String, Float, DateTime, Date, JSON, MetaData, UniqueConstraint
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
    form = Column(String, index=True) # Form 1 or Form 714
    raw_json = Column(JSON)

class EPAData(Base):
    __tablename__ = "epa_data"
    __table_args__ = ({"schema": "raw"}) # Removed UniqueConstraint

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, index=True)
    raw_json = Column(JSON)

class LBNLData(Base):
    __tablename__ = "lbnl_data"
    __table_args__ = ({"schema": "raw"})

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, index=True)
    dataset = Column(String, index=True) # tracking_the_sun, queued_up
    raw_json = Column(JSON)

class ISOData(Base):
    __tablename__ = "iso_data"
    __table_args__ = ({"schema": "raw"})

    id = Column(Integer, primary_key=True, index=True)
    iso = Column(String, index=True) # PJM, CAISO
    dataset = Column(String, index=True) # LMP
    timestamp = Column(DateTime, index=True)
    raw_json = Column(JSON)

# Analysis Schema Models

class Production(Base):
    __tablename__ = "production"
    __table_args__ = (
        UniqueConstraint('date', 'source', 'fuel_type', 'state', name='uix_production_record'),
        {"schema": "analysis"}
    )

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    source = Column(String) # EIA, eGRID
    fuel_type = Column(String)
    value = Column(Float)
    unit = Column(String)
    state = Column(String, nullable=True)

class Consumption(Base):
    __tablename__ = "consumption"
    __table_args__ = (
        UniqueConstraint('date', 'sector', name='uix_consumption_record'),
        {"schema": "analysis"}
    )

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

class Expansion(Base):
    __tablename__ = "expansion"
    __table_args__ = (UniqueConstraint('project_id', name='uix_expansion_record'), {"schema": "analysis"})

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String, index=True)
    status = Column(String) # Planned, Under Construction, Queue
    capacity_mw = Column(Float)
    technology = Column(String)
    location = Column(String) # State/County
    expected_date = Column(Date)

class ConsumptionPrice(Base):
    __tablename__ = "consumption_price"
    __table_args__ = (
        UniqueConstraint('date', 'market_type', 'location', 'customer_class', name='uix_consumption_price_record'),
        {"schema": "analysis"}
    )

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    market_type = Column(String) # Retail, Wholesale Real-Time, Wholesale Day-Ahead
    location = Column(String) # State, Zone, Node
    customer_class = Column(String, nullable=True) # Residential, Industrial, N/A
    price = Column(Float)
    unit = Column(String) # cents/kWh, $/MWh

class ProductionCost(Base):
    __tablename__ = "production_cost"
    __table_args__ = (
        UniqueConstraint('year', 'cost_category', 'metric', 'source', name='uix_production_cost_record'),
        {"schema": "analysis"}
    )

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, index=True)
    cost_category = Column(String) # Fuel, Capital, O&M, Transmission, Taxes, Financing
    metric = Column(String) # Cost per MWh, Total Expense, Installed Cost per Watt
    value = Column(Float)
    unit = Column(String) # $/MWh, USD, $/W
    source = Column(String)

class Maintenance(Base):
    __tablename__ = "maintenance"
    __table_args__ = (UniqueConstraint('asset_id', 'status', name='uix_maintenance_record'), {"schema": "analysis"})

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(String, index=True)
    status = Column(String)
    efficiency_metric = Column(Float, nullable=True)
