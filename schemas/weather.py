"""
Weather Schemas for Phase 2 API Endpoints

Provides Pydantic models for hourly, daily, and historical weather data.
"""

from datetime import date, datetime
from typing import List, Optional, Literal
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class WeatherUnits(str, Enum):
    """Units for weather measurements."""
    METRIC = "metric"
    IMPERIAL = "imperial"


class ResponseFormat(str, Enum):
    """Response format options."""
    JSON = "json"
    CSV = "csv"


class HourlyDataPoint(BaseModel):
    """Single hourly weather data point."""
    time: str = Field(..., description="ISO 8601 timestamp", example="2024-01-15T14:00")
    temperature: float = Field(..., description="Temperature", example=22.5)
    feels_like: Optional[float] = Field(None, description="Feels like temperature", example=21.0)
    humidity: Optional[int] = Field(None, description="Relative humidity %", example=65)
    precipitation: Optional[float] = Field(None, description="Precipitation amount", example=0.0)
    precipitation_probability: Optional[int] = Field(None, description="Precipitation probability %", example=10)
    wind_speed: Optional[float] = Field(None, description="Wind speed", example=5.2)
    wind_direction: Optional[int] = Field(None, description="Wind direction degrees", example=180)
    cloud_cover: Optional[int] = Field(None, description="Cloud cover %", example=40)
    weather_code: Optional[int] = Field(None, description="WMO weather code", example=1)
    uv_index: Optional[float] = Field(None, description="UV index", example=3.5)
    visibility: Optional[float] = Field(None, description="Visibility in meters/miles", example=10000)
    pressure: Optional[float] = Field(None, description="Sea level pressure", example=1013.25)

    class Config:
        json_schema_extra = {
            "example": {
                "time": "2024-01-15T14:00",
                "temperature": 22.5,
                "feels_like": 21.0,
                "humidity": 65,
                "precipitation": 0.0,
                "precipitation_probability": 10,
                "wind_speed": 5.2,
                "wind_direction": 180,
                "cloud_cover": 40,
                "weather_code": 1,
                "uv_index": 3.5,
                "visibility": 10000,
                "pressure": 1013.25
            }
        }


class DailyDataPoint(BaseModel):
    """Single daily weather data point."""
    date: str = Field(..., description="Date in YYYY-MM-DD format", example="2024-01-15")
    temperature_max: float = Field(..., description="Maximum temperature", example=25.0)
    temperature_min: float = Field(..., description="Minimum temperature", example=15.0)
    temperature_mean: Optional[float] = Field(None, description="Mean temperature", example=20.0)
    precipitation_sum: Optional[float] = Field(None, description="Total precipitation", example=2.5)
    precipitation_probability_max: Optional[int] = Field(None, description="Max precipitation probability %", example=40)
    wind_speed_max: Optional[float] = Field(None, description="Maximum wind speed", example=15.0)
    weather_code: Optional[int] = Field(None, description="WMO weather code", example=3)
    sunrise: Optional[str] = Field(None, description="Sunrise time", example="06:45")
    sunset: Optional[str] = Field(None, description="Sunset time", example="18:30")
    uv_index_max: Optional[float] = Field(None, description="Maximum UV index", example=6.0)

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2024-01-15",
                "temperature_max": 25.0,
                "temperature_min": 15.0,
                "temperature_mean": 20.0,
                "precipitation_sum": 2.5,
                "precipitation_probability_max": 40,
                "wind_speed_max": 15.0,
                "weather_code": 3,
                "sunrise": "06:45",
                "sunset": "18:30",
                "uv_index_max": 6.0
            }
        }


class HourlyWeatherRequest(BaseModel):
    """Request model for hourly weather endpoint."""
    lat: float = Field(..., ge=-90, le=90, description="Latitude", example=40.7128)
    lon: float = Field(..., ge=-180, le=180, description="Longitude", example=-74.006)
    hours: Literal[24, 48, 72] = Field(24, description="Number of hours to forecast")
    units: WeatherUnits = Field(WeatherUnits.METRIC, description="Unit system")
    format: ResponseFormat = Field(ResponseFormat.JSON, description="Response format")


class HourlyWeatherResponse(BaseModel):
    """Response model for hourly weather endpoint."""
    latitude: float = Field(..., description="Latitude of the location")
    longitude: float = Field(..., description="Longitude of the location")
    timezone: str = Field(..., description="Timezone of the location", example="America/New_York")
    units: WeatherUnits = Field(..., description="Units used in response")
    generated_at: str = Field(..., description="When this response was generated")
    source: str = Field(..., description="Data source (cache/live)", example="cache")
    hourly: List[HourlyDataPoint] = Field(..., description="Hourly forecast data")

    class Config:
        json_schema_extra = {
            "example": {
                "latitude": 40.71,
                "longitude": -74.01,
                "timezone": "America/New_York",
                "units": "metric",
                "generated_at": "2024-01-15T12:00:00Z",
                "source": "live",
                "hourly": [
                    {
                        "time": "2024-01-15T14:00",
                        "temperature": 22.5,
                        "humidity": 65,
                        "precipitation_probability": 10
                    }
                ]
            }
        }


class DailyWeatherRequest(BaseModel):
    """Request model for daily weather endpoint."""
    lat: float = Field(..., ge=-90, le=90, description="Latitude", example=40.7128)
    lon: float = Field(..., ge=-180, le=180, description="Longitude", example=-74.006)
    days: Literal[7, 14] = Field(7, description="Number of days to forecast")
    units: WeatherUnits = Field(WeatherUnits.METRIC, description="Unit system")
    format: ResponseFormat = Field(ResponseFormat.JSON, description="Response format")


class DailyWeatherResponse(BaseModel):
    """Response model for daily weather endpoint."""
    latitude: float = Field(..., description="Latitude of the location")
    longitude: float = Field(..., description="Longitude of the location")
    timezone: str = Field(..., description="Timezone of the location")
    units: WeatherUnits = Field(..., description="Units used in response")
    generated_at: str = Field(..., description="When this response was generated")
    source: str = Field(..., description="Data source (cache/live)")
    daily: List[DailyDataPoint] = Field(..., description="Daily forecast data")


class HistoricalWeatherRequest(BaseModel):
    """Request model for historical weather endpoint."""
    lat: float = Field(..., ge=-90, le=90, description="Latitude", example=40.7128)
    lon: float = Field(..., ge=-180, le=180, description="Longitude", example=-74.006)
    start: date = Field(..., description="Start date (YYYY-MM-DD)", example="2024-01-01")
    end: date = Field(..., description="End date (YYYY-MM-DD)", example="2024-01-31")
    units: WeatherUnits = Field(WeatherUnits.METRIC, description="Unit system")
    format: ResponseFormat = Field(ResponseFormat.JSON, description="Response format")

    @field_validator('end')
    @classmethod
    def validate_date_range(cls, v: date, info) -> date:
        """Validate that date range is not more than 1 year."""
        start = info.data.get('start')
        if start and v:
            diff = (v - start).days
            if diff > 365:
                raise ValueError("Date range cannot exceed 1 year (365 days)")
            if diff < 0:
                raise ValueError("End date must be after start date")
        return v


class HistoricalWeatherResponse(BaseModel):
    """Response model for historical weather endpoint."""
    latitude: float = Field(..., description="Latitude of the location")
    longitude: float = Field(..., description="Longitude of the location")
    timezone: str = Field(..., description="Timezone of the location")
    units: WeatherUnits = Field(..., description="Units used in response")
    start_date: str = Field(..., description="Start date of data")
    end_date: str = Field(..., description="End date of data")
    generated_at: str = Field(..., description="When this response was generated")
    source: str = Field(..., description="Data source (cache/live)")
    daily: List[DailyDataPoint] = Field(..., description="Historical daily data")
