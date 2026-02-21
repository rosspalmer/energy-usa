import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/energyusa_historical")
    EIA_API_KEY = os.getenv("EIA_API_KEY")
    NREL_API_KEY = os.getenv("NREL_API_KEY")

