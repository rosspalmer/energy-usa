import requests
import pandas as pd
import io
from energyusa.extractors.base import BaseExtractor
from energyusa.database import SessionLocal
from energyusa.models import FERCData, EPAData

class FileExtractor(BaseExtractor):
    # FERC Form 714 (Hourly Load Data) - Example URL for 2022
    FERC_URL_TEMPLATE = "https://www.ferc.gov/sites/default/files/2023-06/Form-714-Data-Viewer-Map-2022.xlsx" 
    
    # EPA eGRID - 2021 Data (published Jan 2023)
    EGRID_URL = "https://www.epa.gov/system/files/documents/2023-01/eGRID2021_data.xlsx"

    def extract(self, mode: str = "refresh", start_date: str = None, end_date: str = None):
        self._extract_ferc(mode, start_date)
        self._extract_epa(mode, start_date)

    def _extract_ferc(self, mode: str, start_date: str = None):
        # FERC extraction logic
        # Real implementation: Download CSV/Excel, parse specific sheets (Planning Area Hourly Demand)
        session = SessionLocal()
        try:
            print("Simulating FERC Form 714 download...")
            # Use start_date year if provided
            target_year = 2022
            if start_date:
                try:
                    target_year = int(start_date[:4])
                except ValueError:
                    pass

            # Create dummy data representing what we'd parse
            dummy_data = [
                {"report_year": target_year, "respondent_id": 101, "hour_01": 1500, "hour_02": 1450},
                {"report_year": target_year, "respondent_id": 102, "hour_01": 3000, "hour_02": 2900}
            ]
            
            for row in dummy_data:
                db_rec = FERCData(
                    report_year=row['report_year'],
                    raw_json=row
                )
                session.add(db_rec)
            
            session.commit()
            print("Stored FERC data.")

        except Exception as e:
            print(f"Error extracting FERC: {e}")
            session.rollback()
        finally:
            session.close()

    def _extract_epa(self, mode: str, start_date: str = None):
        session = SessionLocal()
        try:
            print("Simulating EPA eGRID download...")
            
            target_year = 2021
            if start_date:
                try:
                    target_year = int(start_date[:4])
                except ValueError:
                    pass
            
            dummy_data = [
                {"year": target_year, "plant_id": 123, "plant_name": "Plant A", "net_gen": 50000, "co2_emissions": 1000},
                {"year": target_year, "plant_id": 124, "plant_name": "Plant B", "net_gen": 75000, "co2_emissions": 0}
            ]

            for row in dummy_data:
                db_rec = EPAData(
                    year=row['year'],
                    raw_json=row
                )
                session.add(db_rec)
            
            session.commit()
            print("Stored EPA data.")
            
        except Exception as e:
            print(f"Error extracting EPA: {e}")
            session.rollback()
        finally:
            session.close()
