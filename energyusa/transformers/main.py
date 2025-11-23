import pandas as pd
from sqlalchemy import text
from energyusa.database import engine
from energyusa.models import Production, Consumption

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
            # Mapping SEDS 'MSN' codes to logic is complex.
            # Assuming 'CLTCB' (Coal Total Consumption) for consumption example
            # Assuming 'CLPRB' (Coal Production) for production example
            # For MVP, we just take the value and assume it's 'Consumption' if not specified
            
            # Example Transformation
            if 'period' in raw:
                date_val = pd.to_datetime(raw['period'], format='%Y')
                
                # Naive mapping
                record = {
                    'date': date_val,
                    'sector': 'All', # Simplified
                    'value': float(raw.get('value', 0) or 0),
                    'unit': raw.get('unit', 'BTU')
                }
                
                # Insert into Consumption (Analysis)
                # Using core insert for performance or ORM
                # We'll use ORM logic via a quick bulk construct or just loop for clarity in MVP
                # But standard SQL insert is better for 'transform' step to avoid session overhead
                
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
            # Map to Production
            record = {
                'date': pd.to_datetime(str(raw.get('year')), format='%Y'),
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

