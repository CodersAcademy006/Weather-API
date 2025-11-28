"""
Pydantic Schemas for IntelliWeather API

This module provides request/response models with validation and OpenAPI documentation.
"""

from schemas.weather import (
    HourlyWeatherRequest,
    HourlyWeatherResponse,
    DailyWeatherRequest,
    DailyWeatherResponse,
    HistoricalWeatherRequest,
    HistoricalWeatherResponse,
    HourlyDataPoint,
    DailyDataPoint,
    WeatherUnits,
    ResponseFormat
)

from schemas.geocode import (
    GeocodeSearchRequest,
    GeocodeSearchResponse,
    ReverseGeocodeRequest,
    ReverseGeocodeResponse,
    GeoLocation
)

from schemas.alerts import (
    WeatherAlert,
    AlertsResponse,
    AlertSeverity
)

from schemas.api_keys import (
    APIKeyCreate,
    APIKeyResponse,
    APIKeyList
)

__all__ = [
    # Weather
    "HourlyWeatherRequest",
    "HourlyWeatherResponse",
    "DailyWeatherRequest",
    "DailyWeatherResponse",
    "HistoricalWeatherRequest",
    "HistoricalWeatherResponse",
    "HourlyDataPoint",
    "DailyDataPoint",
    "WeatherUnits",
    "ResponseFormat",
    # Geocode
    "GeocodeSearchRequest",
    "GeocodeSearchResponse",
    "ReverseGeocodeRequest",
    "ReverseGeocodeResponse",
    "GeoLocation",
    # Alerts
    "WeatherAlert",
    "AlertsResponse",
    "AlertSeverity",
    # API Keys
    "APIKeyCreate",
    "APIKeyResponse",
    "APIKeyList",
]
