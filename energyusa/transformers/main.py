import pandas as pd
from sqlalchemy import text
from energyusa.database import engine
from energyusa.models import Production, Consumption
import json

def transform_eia_data():
    """
    Reads from raw.eia_data, transforms, and inserts into analysis tables.
    """
    query = text("SELECT * FROM raw.eia_data")
    
    # Use pandas to read sql
    df = pd.read_sql(query, engine)
    
    if df.empty:
        print("No EIA data to transform.")
        return

    # Separate SEDS vs Electricity based on api_path or content
    # Simple logic for MVP: if api_path contains 'seds' -> Consumption/Production
    
    seds_df = df[df['api_path'].str.contains('seds', na=False)]
    
    with engine.connect() as conn:
        # Transform SEDS
        for _, row in seds_df.iterrows():
            raw = row['raw_json']
            
            if isinstance(raw, str):
                try:
                    raw = json.loads(raw)
                except json.JSONDecodeError:
                    continue
            
            # Example Transformation
            if 'period' in raw:
                date_val = pd.to_datetime(raw['period'], format='%Y')
                
                # Naive mapping
                record = {
                    # Convert pandas Timestamp to python datetime or string for SQL compatibility
                    'date': date_val.to_pydatetime(),
                    'sector': 'All', # Simplified
                    'value': float(raw.get('value', 0) or 0),
                    'unit': raw.get('unit', 'BTU')
                }
                
                conn.execute(
                    text("INSERT INTO analysis.consumption (date, sector, value, unit) VALUES (:date, :sector, :value, :unit)"),
                    record
                )
        
        conn.commit()
    print("Transformed EIA data.")

def transform_epa_data():
    query = text("SELECT * FROM raw.epa_data")
    df = pd.read_sql(query, engine)
    
    if df.empty:
        print("No EPA data to transform.")
        return

    with engine.connect() as conn:
        for _, row in df.iterrows():
            raw = row['raw_json']
            
            if isinstance(raw, str):
                try:
                    raw = json.loads(raw)
                except json.JSONDecodeError:
                    continue

            # Map to Production
            date_val = pd.to_datetime(str(raw.get('year')), format='%Y')
            
            record = {
                'date': date_val.to_pydatetime(),
                'source': 'eGRID',
                'fuel_type': 'Mix',
                'value': float(raw.get('net_gen', 0)),
                'unit': 'MWh',
                'state': 'US'
            }
            
            conn.execute(
                text("""
                    INSERT INTO analysis.production (date, source, fuel_type, value, unit, state) 
                    VALUES (:date, :source, :fuel_type, :value, :unit, :state)
                """),
                record
            )
        conn.commit()
    print("Transformed EPA data.")
