import pytest
from unittest.mock import patch, MagicMock
from energyusa.extractors.eia import EIAExtractor
from energyusa.models import EIAData
from energyusa.config import Config

def test_eia_extractor_initialization(monkeypatch):
    # Patch Config attributes directly since it might be loaded already
    monkeypatch.setattr(Config, "EIA_API_KEY", "test_key")
    extractor = EIAExtractor()
    assert extractor.api_key == "test_key"

@patch("energyusa.extractors.eia.requests.get")
def test_eia_extraction(mock_get, db_session, monkeypatch):
    monkeypatch.setattr(Config, "EIA_API_KEY", "test_key")
    
    # Mock API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "response": {
            "data": [
                {"period": "2023-01-01T00", "value": 100, "respondent": "US"},
                {"period": "2023-01-01T01", "value": 120, "respondent": "US"}
            ]
        }
    }
    mock_get.return_value = mock_response
    
    extractor = EIAExtractor()
    
    # We need to patch SessionLocal to return our test db_session
    with patch("energyusa.extractors.eia.SessionLocal", return_value=db_session):
        extractor.extract(mode="refresh")
    
    # Verify data was inserted into the DB
    results = db_session.query(EIAData).all()
    assert len(results) >= 2 
    
    # Check specific values
    elec_record = next((r for r in results if r.value == 100), None)
    assert elec_record is not None
    assert elec_record.api_path == "electricity/rto/region-data"
