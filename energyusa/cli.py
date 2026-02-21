import typer
from typing import Optional
from sqlalchemy import inspect, text
from sqlalchemy.schema import CreateSchema
from energyusa.database import engine
from energyusa.models import Base
from energyusa.extractors.eia import EIAExtractor
from energyusa.extractors.files import FileExtractor
from energyusa.transformers.main import transform_eia_data, transform_epa_data
from energyusa.display.service import get_production_data

app = typer.Typer()

@app.command()
def setup_db(reset: bool = False):
    """Initialize the database with schemas and tables."""
    inspector = inspect(engine)
    existing_schemas = inspector.get_schema_names()

    with engine.connect() as connection:
        if "raw" not in existing_schemas:
            connection.execute(CreateSchema("raw"))
            print("Created schema: raw")
        if "analysis" not in existing_schemas:
            connection.execute(CreateSchema("analysis"))
            print("Created schema: analysis")
        
        if reset:
            print("Resetting database tables...")
            # Drop all tables in reverse dependency order
            Base.metadata.drop_all(bind=engine)
            print("Dropped all tables.")
            
        connection.commit()

    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")

@app.command()
def extract(
    source: str, 
    mode: str = "refresh", 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None
):
    """Extract data from a source (eia, files)."""
    if source == "eia":
        extractor = EIAExtractor()
        extractor.extract(mode, start_date=start_date, end_date=end_date)
    elif source == "files":
        extractor = FileExtractor()
        extractor.extract(mode, start_date=start_date, end_date=end_date)
    else:
        typer.echo(f"Unknown source: {source}")

@app.command()
def analyze(category: str = "all"):
    """Run transformations."""
    typer.echo("Running transformations...")
    transform_eia_data()
    transform_epa_data()
    typer.echo("Analysis complete.")

@app.command()
def show_production():
    """Display recent production data."""
    data = get_production_data()
    for record in data:
        typer.echo(record)

if __name__ == "__main__":
    app()
