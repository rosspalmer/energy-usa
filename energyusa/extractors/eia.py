import requests
from datetime import datetime
from energyusa.extractors.base import BaseExtractor
from energyusa.config import Config
from energyusa.database import SessionLocal
from energyusa.models import EIAData
from sqlalchemy.dialects.postgresql import insert

class EIAExtractor(BaseExtractor):
    BASE_URL = "https://api.eia.gov/v2/"

    def __init__(self):
        self.api_key = Config.EIA_API_KEY
        if not self.api_key:
            raise ValueError("EIA_API_KEY not found in config")

    def extract(self, mode: str = "refresh", start_date: str = None, end_date: str = None):
        """
        Extract data from EIA API.
        """
        self._extract_electricity(mode, start_date, end_date)
        self._extract_seds(mode, start_date, end_date)
        self._extract_monthly_generation(mode, start_date, end_date)
        self._extract_retail_sales(mode, start_date, end_date)
        self._extract_operating_data(mode, start_date, end_date)
        self._extract_interchange(mode, start_date, end_date)
        self._extract_generator_construction(mode, start_date, end_date)

    def _get_start_date(self, mode, start_date, historical_default, recent_months=1):
        if start_date:
            return start_date
        elif mode == "historical":
            return historical_default
        else:
            # Recent data
            now = datetime.now()
            try:
                effective = now.replace(month=now.month - recent_months).strftime("%Y-%m-%d")
            except ValueError:
                # Handle January edge case by going back to previous year
                year = now.year
                month = now.month - recent_months
                while month <= 0:
                    month += 12
                    year -= 1
                effective = now.replace(year=year, month=month).strftime("%Y-%m-%d")
            return effective

    def _extract_electricity(self, mode: str, start_date: str = None, end_date: str = None):
        # Example: Electricity Operating Data (Hourly)
        # Path: electricity/rto/region-data
        
        effective_start = self._get_start_date(mode, start_date, "2020-01-01")

        url = f"{self.BASE_URL}electricity/rto/region-data/data/"
        params = {
            "api_key": self.api_key,
            "frequency": "hourly",
            "data[0]": "value",
            "start": effective_start,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "offset": 0,
            "length": 5000 # Limit for MVP chunks
        }
        
        if end_date:
            params["end"] = end_date
        
        self._fetch_and_store(url, params, "electricity/rto/region-data")

    def _extract_seds(self, mode: str, start_date: str = None, end_date: str = None):
        # State Energy Data System (SEDS)
        # Path: seds/data
        
        # SEDS uses years
        if start_date:
            effective_start = start_date[:4]
        elif mode == "historical":
            effective_start = "2010"
        else:
            effective_start = str(datetime.now().year - 1)

        url = f"{self.BASE_URL}seds/data/"
        params = {
            "api_key": self.api_key,
            "frequency": "annual",
            "data[0]": "value",
            "start": effective_start,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "offset": 0,
            "length": 5000
        }
        
        if end_date:
            params["end"] = end_date[:4]

        self._fetch_and_store(url, params, "seds/data")

    def _extract_monthly_generation(self, mode: str, start_date: str = None, end_date: str = None):
        # Path: electricity/electric-power-operational-data (New v2 replacement for monthly/generation)
        effective_start = self._get_start_date(mode, start_date, "2020-01")
        if len(effective_start) > 7:
             effective_start = effective_start[:7]

        url = f"{self.BASE_URL}electricity/electric-power-operational-data/data/"
        params = {
            "api_key": self.api_key,
            "frequency": "monthly",
            "data[0]": "generation",
            "start": effective_start,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "offset": 0,
            "length": 5000
        }
        if end_date:
             params["end"] = end_date[:7] if len(end_date) > 7 else end_date

        self._fetch_and_store(url, params, "electricity/electric-power-operational-data")

    def _extract_retail_sales(self, mode: str, start_date: str = None, end_date: str = None):
        # Path: electricity/retail-sales
        effective_start = self._get_start_date(mode, start_date, "2020-01")
        if len(effective_start) > 7:
             effective_start = effective_start[:7]

        url = f"{self.BASE_URL}electricity/retail-sales/data/"
        params = {
            "api_key": self.api_key,
            "frequency": "monthly",
            "data[0]": "sales",
            "data[1]": "price",
            "start": effective_start,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "offset": 0,
            "length": 5000
        }
        if end_date:
             params["end"] = end_date[:7] if len(end_date) > 7 else end_date

        self._fetch_and_store(url, params, "electricity/retail-sales")

    def _extract_operating_data(self, mode: str, start_date: str = None, end_date: str = None):
        # Path: electricity/facility-fuel (Replacement for operating-data costs/receipts)
        # Note: This endpoint provides fuel costs and qualities
        effective_start = self._get_start_date(mode, start_date, "2020-01")
        if len(effective_start) > 7:
             effective_start = effective_start[:7]

        url = f"{self.BASE_URL}electricity/facility-fuel/data/"
        params = {
            "api_key": self.api_key,
            "frequency": "monthly",
            "data[0]": "fuel_cost", # Updated column name for v2 facility-fuel
            "start": effective_start,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "offset": 0,
            "length": 5000
        }
        if end_date:
             params["end"] = end_date[:7] if len(end_date) > 7 else end_date

        self._fetch_and_store(url, params, "electricity/facility-fuel")

    def _extract_interchange(self, mode: str, start_date: str = None, end_date: str = None):
        # Path: electricity/rto/interchange-data
        effective_start = self._get_start_date(mode, start_date, "2020-01-01")

        url = f"{self.BASE_URL}electricity/rto/interchange-data/data/"
        params = {
            "api_key": self.api_key,
            "frequency": "hourly",
            "data[0]": "value",
            "start": effective_start,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "offset": 0,
            "length": 5000
        }
        if end_date:
             params["end"] = end_date

        self._fetch_and_store(url, params, "electricity/rto/interchange-data")
    
    def _extract_generator_construction(self, mode: str, start_date: str = None, end_date: str = None):
        # Path: electricity/operating-generator-capacity (New v2 replacement for generators capacity)
        # Extracting annual data for status and planned capacity
        effective_start = self._get_start_date(mode, start_date, "2020")
        if len(effective_start) > 4:
             effective_start = effective_start[:4] # Annual

        url = f"{self.BASE_URL}electricity/operating-generator-capacity/data/"
        params = {
            "api_key": self.api_key,
            "frequency": "annual",
            "data[0]": "summer_capacity_mw", # Available capacity metric
            "data[1]": "technology",
            "data[2]": "status",
            "start": effective_start,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "offset": 0,
            "length": 5000
        }
        if end_date:
             params["end"] = end_date[:4] if len(end_date) > 4 else end_date

        self._fetch_and_store(url, params, "electricity/operating-generator-capacity")

    def _fetch_and_store(self, url, params, api_path_tag):
        session = SessionLocal()
        try:
            # Simplified fetching logic: handle pagination if needed in future, for now limit to length
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "response" in data and "data" in data["response"]:
                records = data["response"]["data"]
                
                for record in records:
                    # Handle missing value field if we requested multiple data fields
                    val = 0.0
                    # Robust value extraction based on potential column names in v2
                    if "value" in record:
                        val = float(record.get("value", 0) or 0)
                    elif "generation" in record:
                        val = float(record.get("generation", 0) or 0)
                    elif "sales" in record:
                        val = float(record.get("sales", 0) or 0)
                    elif "fuel_cost" in record:
                        val = float(record.get("fuel_cost", 0) or 0)
                    elif "cost" in record:
                        val = float(record.get("cost", 0) or 0)
                    elif "summer_capacity_mw" in record:
                        val = float(record.get("summer_capacity_mw", 0) or 0)
                    elif "planned_generation_capacity_mw" in record:
                        val = float(record.get("planned_generation_capacity_mw", 0) or 0)

                    db_rec = EIAData(
                        api_path=api_path_tag,
                        period=str(record.get("period")),
                        value=val,
                        raw_json=record
                    )
                    session.add(db_rec)
                
                session.commit()
                print(f"Stored {len(records)} records for {api_path_tag}")
            else:
                print(f"No data found for {api_path_tag}")

        except Exception as e:
            print(f"Error fetching {api_path_tag}: {e}")
            session.rollback()
        finally:
            session.close()
