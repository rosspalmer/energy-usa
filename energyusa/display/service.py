from typing import List
from energyusa.database import SessionLocal
from energyusa.models import Production, Consumption
from energyusa.display.schemas import ProductionRecord, ConsumptionRecord

def get_production_data(limit: int = 100) -> List[ProductionRecord]:
    session = SessionLocal()
    try:
        records = session.query(Production).limit(limit).all()
        return [ProductionRecord.model_validate(r) for r in records]
    finally:
        session.close()

def get_consumption_data(limit: int = 100) -> List[ConsumptionRecord]:
    session = SessionLocal()
    try:
        records = session.query(Consumption).limit(limit).all()
        return [ConsumptionRecord.model_validate(r) for r in records]
    finally:
        session.close()

