"""
Pytest configuration and fixtures for Weather API tests.
"""
import os
import pytest
import sqlite3
import tempfile
from datetime import datetime, timezone

from fastapi.testclient import TestClient


@pytest.fixture(scope="function")
def temp_db():
    """Create a temporary database file for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    # Cleanup
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture(scope="function")
def test_client(temp_db, monkeypatch):
    """Create a test client with isolated database."""
    # Patch the database file path before importing app
    monkeypatch.setenv("WEATHER_DB_FILE", temp_db)
    
    # Import app module and patch DB_FILE
    import app
    monkeypatch.setattr(app, "DB_FILE", temp_db)
    
    # Initialize the database
    app.init_db()
    
    # Create test client
    client = TestClient(app.app)
    yield client


@pytest.fixture
def sample_weather_data():
    """Sample weather data for testing."""
    return {
        "location_name": "Test_Location",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "timestamp": datetime.now(timezone.utc),
        "temperature_c": 22.5,
        "humidity_pct": 65,
        "pressure_hpa": 1013.25,
        "wind_speed_mps": 5.5,
        "precip_mm": 0.0,
        "weather_code": 0,
        "apparent_temperature": 21.0,
        "uv_index": 5.0,
        "is_day": 1
    }


@pytest.fixture
def sample_hourly_forecast():
    """Sample hourly forecast data for DB testing (uses save_hourly_forecast_to_db field names)."""
    return [
        {
            "time": "2024-01-15T10:00",
            "temp": 22.0,
            "precip_prob": 10,
            "wind": 3.5,
            "cloud_cover": 20,
            "weather_code": 1
        },
        {
            "time": "2024-01-15T11:00",
            "temp": 23.5,
            "precip_prob": 15,
            "wind": 4.0,
            "cloud_cover": 25,
            "weather_code": 2
        }
    ]


@pytest.fixture
def sample_daily_forecast():
    """Sample daily forecast data for testing."""
    return [
        {
            "date": "2024-01-15",
            "max_temp": 25.0,
            "min_temp": 15.0,
            "weather_code": 0,
            "sunrise": "07:00",
            "sunset": "17:30",
            "precipitation_sum": 0.0,
            "precipitation_probability_max": 10
        },
        {
            "date": "2024-01-16",
            "max_temp": 23.0,
            "min_temp": 14.0,
            "weather_code": 2,
            "sunrise": "07:01",
            "sunset": "17:31",
            "precipitation_sum": 2.5,
            "precipitation_probability_max": 45
        }
    ]


@pytest.fixture
def initialized_db(temp_db, monkeypatch):
    """Create an initialized database with tables."""
    import app
    monkeypatch.setattr(app, "DB_FILE", temp_db)
    app.init_db()
    return temp_db
