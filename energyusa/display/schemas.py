from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ProductionRecord(BaseModel):
    date: datetime
    source: str
    fuel_type: str
    value: float
    unit: str
    state: Optional[str] = None

    class Config:
        from_attributes = True

class ConsumptionRecord(BaseModel):
    date: datetime
    sector: str
    value: float
    unit: str

    class Config:
        from_attributes = True

