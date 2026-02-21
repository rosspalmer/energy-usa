import pandas as pd
from sqlalchemy import text
from energyusa.database import engine
from energyusa.models import Production, Consumption, Transmission, Expansion, ConsumptionPrice, ProductionCost
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

    # Filter dataframes by api_path for processing
    seds_df = df[df['api_path'].str.contains('seds/data', na=False)]
    gen_df = df[df['api_path'].str.contains('electricity/electric-power-operational-data', na=False)]
    sales_df = df[df['api_path'].str.contains('electricity/retail-sales', na=False)]
    ops_df = df[df['api_path'].str.contains('electricity/facility-fuel', na=False)]
    interchange_df = df[df['api_path'].str.contains('electricity/rto/interchange-data', na=False)]
    construction_df = df[df['api_path'].str.contains('electricity/operating-generator-capacity', na=False)]
    
    with engine.connect() as conn:
        # 1. Transform SEDS -> Consumption
        if not seds_df.empty:
            for _, row in seds_df.iterrows():
                raw = _parse_json(row['raw_json'])
                if not raw or 'period' not in raw: continue
                
                date_val = pd.to_datetime(raw['period'], format='%Y')
                record = {
                    'date': date_val.to_pydatetime(),
                    'sector': 'All', 
                    'value': float(raw.get('value', 0) or 0),
                    'unit': raw.get('unit', 'BTU')
                }
                conn.execute(
                    text("""
                        INSERT INTO analysis.consumption (date, sector, value, unit) 
                        VALUES (:date, :sector, :value, :unit)
                        ON CONFLICT (date, sector) DO UPDATE SET value = EXCLUDED.value
                    """),
                    record
                )
        
        # 2. Transform Monthly Generation -> Production (Updated for electric-power-operational-data)
        if not gen_df.empty:
             for _, row in gen_df.iterrows():
                raw = _parse_json(row['raw_json'])
                if not raw or 'period' not in raw: continue

                # Handle YYYY-MM format
                date_val = pd.to_datetime(raw['period'])
                
                record = {
                    'date': date_val.to_pydatetime(),
                    'source': 'EIA',
                    'fuel_type': raw.get('energy-source-description', raw.get('energy_source_description', 'Unknown')),
                    'value': float(raw.get('generation', 0) or 0),
                    'unit': raw.get('generation-units', 'MWh'),
                    'state': raw.get('location', raw.get('state', 'US')) # location field in v2 often used for state
                }
                conn.execute(
                    text("""
                        INSERT INTO analysis.production (date, source, fuel_type, value, unit, state) 
                        VALUES (:date, :source, :fuel_type, :value, :unit, :state)
                        ON CONFLICT (date, source, fuel_type, state) DO UPDATE SET value = EXCLUDED.value
                    """),
                    record
                )

        # 3. Transform Retail Sales -> Consumption & Consumption Price
        if not sales_df.empty:
             for _, row in sales_df.iterrows():
                raw = _parse_json(row['raw_json'])
                if not raw or 'period' not in raw: continue
                
                date_val = pd.to_datetime(raw['period'])
                
                # Consumption
                if 'sales' in raw:
                    cons_record = {
                        'date': date_val.to_pydatetime(),
                        'sector': raw.get('sector_name', 'All'),
                        'value': float(raw.get('sales', 0) or 0),
                        'unit': raw.get('sales-units', 'MWh')
                    }
                    conn.execute(
                        text("""
                            INSERT INTO analysis.consumption (date, sector, value, unit) 
                            VALUES (:date, :sector, :value, :unit)
                            ON CONFLICT (date, sector) DO UPDATE SET value = EXCLUDED.value
                        """),
                        cons_record
                    )

                # Price
                if 'price' in raw:
                     price_record = {
                        'date': date_val.to_pydatetime(),
                        'market_type': 'Retail',
                        'location': raw.get('stateid', 'US'),
                        'customer_class': raw.get('sector_name', 'All'),
                        'price': float(raw.get('price', 0) or 0),
                        'unit': raw.get('price-units', 'cents/kWh')
                     }
                     conn.execute(
                        text("""
                            INSERT INTO analysis.consumption_price (date, market_type, location, customer_class, price, unit) 
                            VALUES (:date, :market_type, :location, :customer_class, :price, :unit)
                            ON CONFLICT (date, market_type, location, customer_class) DO UPDATE SET price = EXCLUDED.price
                        """),
                        price_record
                     )

        # 4. Transform Operating Data -> Production Cost (Fuel) (Updated for facility-fuel)
        if not ops_df.empty:
             for _, row in ops_df.iterrows():
                raw = _parse_json(row['raw_json'])
                if not raw or 'period' not in raw: continue
                
                date_val = pd.to_datetime(raw['period'])
                year = date_val.year
                
                if 'fuel_cost' in raw:
                    cost_record = {
                        'year': year,
                        'cost_category': 'Fuel',
                        'metric': f"Fuel Cost - {raw.get('energy-source-description', 'Unknown')}",
                        'value': float(raw.get('fuel_cost', 0) or 0),
                        'unit': raw.get('fuel_cost-units', 'cents/MMBtu'), 
                        'source': 'EIA'
                    }
                    conn.execute(
                        text("""
                            INSERT INTO analysis.production_cost (year, cost_category, metric, value, unit, source) 
                            VALUES (:year, :cost_category, :metric, :value, :unit, :source)
                            ON CONFLICT (year, cost_category, metric, source) DO UPDATE SET value = EXCLUDED.value
                        """),
                        cost_record
                    )

        # 5. Transform Interchange -> Transmission
        if not interchange_df.empty:
             for _, row in interchange_df.iterrows():
                raw = _parse_json(row['raw_json'])
                if not raw or 'period' not in raw: continue
                
                # Use UTC or appropriate timezone handling if needed
                date_val = pd.to_datetime(raw['period'])
                
                # Typically interchange is between BAs. 
                # We store one record per flow or simplified.
                # 'fromba' and 'toba' are usually fields.
                ba = f"{raw.get('fromba')}->{raw.get('toba')}"
                
                trans_record = {
                    'timestamp': date_val.to_pydatetime(),
                    'balancing_authority': ba,
                    'interchange_value': float(raw.get('value', 0) or 0)
                }
                conn.execute(
                    text("""
                        INSERT INTO analysis.transmission (timestamp, balancing_authority, interchange_value) 
                        VALUES (:timestamp, :balancing_authority, :interchange_value)
                        ON CONFLICT (timestamp, balancing_authority) DO UPDATE SET interchange_value = EXCLUDED.interchange_value
                    """),
                    trans_record
                )

        # 6. Transform Generators -> Expansion (Updated for operating-generator-capacity)
        if not construction_df.empty:
             for _, row in construction_df.iterrows():
                raw = _parse_json(row['raw_json'])
                if not raw: continue
                
                # Determine expected date if available, or use period
                # operating-generator-capacity is usually annual status snapshots
                expected_date = None
                if 'period' in raw:
                     try:
                        expected_date = pd.to_datetime(raw['period']).date()
                     except:
                        pass
                
                # Construct a unique project ID if generator_id is missing (aggregated data)
                # or use provided ID. v2 endpoint might aggregate.
                # If aggregated by state/fuel, project_id needs to reflect that.
                # Assuming granular data for now or handling aggregation key.
                # Use state + fuel + prime mover as key if id missing.
                proj_id = f"{raw.get('stateid', raw.get('location', 'US'))}-{raw.get('energy_source_code', 'ALL')}-{raw.get('prime_mover_code', 'ALL')}"
                
                exp_record = {
                    'project_id': proj_id,
                    'status': raw.get('status_description', 'Operating'), # Field name check
                    'capacity_mw': float(raw.get('summer_capacity_mw', 0) or 0),
                    'technology': raw.get('energy_source_description', 'Unknown'),
                    'location': raw.get('stateid', raw.get('location', 'US')),
                    'expected_date': expected_date
                }
                
                conn.execute(
                    text("""
                        INSERT INTO analysis.expansion (project_id, status, capacity_mw, technology, location, expected_date) 
                        VALUES (:project_id, :status, :capacity_mw, :technology, :location, :expected_date)
                        ON CONFLICT (project_id) DO UPDATE 
                        SET status = EXCLUDED.status, 
                            capacity_mw = EXCLUDED.capacity_mw, 
                            expected_date = EXCLUDED.expected_date
                    """),
                    exp_record
                )

        conn.commit()
    print("Transformed EIA data.")

def _parse_json(raw):
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    return raw

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
            
            # Note: Production constraint is (date, source, fuel_type, state). 
            # Ensure these match the unique constraint for proper upsert.
            conn.execute(
                text("""
                    INSERT INTO analysis.production (date, source, fuel_type, value, unit, state) 
                    VALUES (:date, :source, :fuel_type, :value, :unit, :state)
                    ON CONFLICT (date, source, fuel_type, state) DO UPDATE SET value = EXCLUDED.value
                """),
                record
            )
        conn.commit()
    print("Transformed EPA data.")
