"""
Forecast Routes - Enhanced Multi-Source Weather Forecasting

Provides comprehensive forecast capabilities:
- Nowcast (0-2 hours, high resolution)
- Hourly forecasts up to 48 hours
- Daily forecasts up to 16 days
- Hybrid Open-Meteo + WeatherAPI for reliability
"""

import requests
from datetime import datetime, timezone, timedelta
from typing import Optional, Literal, Dict, Any, List

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from config import settings
from logging_config import get_logger
from cache import get_cache, generate_weather_cache_key
from metrics import get_metrics
from schemas.weather import WeatherUnits, ResponseFormat

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v3/forecast", tags=["Forecast V3"])


# ==================== HELPER FUNCTIONS ====================

def fetch_open_meteo_nowcast(lat: float, lon: float) -> Optional[Dict]:
    """
    Fetch high-resolution nowcast (0-2 hours) from Open-Meteo.
    Uses minutely_15 for 15-minute resolution.
    """
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "minutely_15": [
                "temperature_2m",
                "precipitation",
                "precipitation_probability",
                "weather_code",
                "wind_speed_10m",
                "wind_direction_10m",
                "relative_humidity_2m"
            ],
            "forecast_hours": 2,
            "timezone": "auto"
        }
        
        response = requests.get(
            settings.OPEN_METEO_API_URL,
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"Fetched nowcast from Open-Meteo for {lat},{lon}")
            return response.json()
        else:
            logger.warning(f"Open-Meteo nowcast failed: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching Open-Meteo nowcast: {e}")
        return None


def fetch_open_meteo_hourly(lat: float, lon: float, hours: int = 48) -> Optional[Dict]:
    """
    Fetch hourly forecast from Open-Meteo.
    Supports up to 168 hours (7 days).
    """
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": [
                "temperature_2m",
                "apparent_temperature",
                "precipitation",
                "precipitation_probability",
                "weather_code",
                "wind_speed_10m",
                "wind_direction_10m",
                "wind_gusts_10m",
                "relative_humidity_2m",
                "dew_point_2m",
                "pressure_msl",
                "cloud_cover",
                "visibility",
                "uv_index",
                "snowfall"
            ],
            "forecast_hours": min(hours, 168),
            "timezone": "auto"
        }
        
        response = requests.get(
            settings.OPEN_METEO_API_URL,
            params=params,
            timeout=15
        )
        
        if response.status_code == 200:
            logger.info(f"Fetched hourly forecast from Open-Meteo for {lat},{lon}")
            return response.json()
        else:
            logger.warning(f"Open-Meteo hourly failed: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching Open-Meteo hourly: {e}")
        return None


def fetch_open_meteo_daily(lat: float, lon: float, days: int = 16) -> Optional[Dict]:
    """
    Fetch daily forecast from Open-Meteo.
    Supports up to 16 days.
    """
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "apparent_temperature_max",
                "apparent_temperature_min",
                "precipitation_sum",
                "precipitation_probability_max",
                "precipitation_hours",
                "weather_code",
                "sunrise",
                "sunset",
                "wind_speed_10m_max",
                "wind_gusts_10m_max",
                "wind_direction_10m_dominant",
                "uv_index_max",
                "snowfall_sum"
            ],
            "forecast_days": min(days, 16),
            "timezone": "auto"
        }
        
        response = requests.get(
            settings.OPEN_METEO_API_URL,
            params=params,
            timeout=15
        )
        
        if response.status_code == 200:
            logger.info(f"Fetched daily forecast from Open-Meteo for {lat},{lon}")
            return response.json()
        else:
            logger.warning(f"Open-Meteo daily failed: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching Open-Meteo daily: {e}")
        return None


def fetch_weatherapi_forecast(lat: float, lon: float, days: int = 14) -> Optional[Dict]:
    """
    Fetch forecast from WeatherAPI.com as fallback/hybrid source.
    Supports up to 14 days.
    """
    try:
        if not settings.WEATHERAPI_KEY:
            return None
            
        params = {
            "key": settings.WEATHERAPI_KEY,
            "q": f"{lat},{lon}",
            "days": min(days, 14),
            "aqi": "yes",
            "alerts": "yes"
        }
        
        response = requests.get(
            settings.WEATHERAPI_URL,
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"Fetched forecast from WeatherAPI for {lat},{lon}")
            return response.json()
        else:
            logger.warning(f"WeatherAPI forecast failed: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching WeatherAPI forecast: {e}")
        return None


def merge_forecasts(open_meteo: Dict, weatherapi: Optional[Dict]) -> Dict:
    """
    Merge Open-Meteo and WeatherAPI data for hybrid reliability.
    Open-Meteo is primary, WeatherAPI fills gaps and provides additional data.
    """
    merged = open_meteo.copy()
    
    if not weatherapi:
        return merged
    
    # Add WeatherAPI-specific data if available
    if "current" in weatherapi:
        merged["weatherapi_current"] = {
            "condition": weatherapi["current"].get("condition", {}).get("text"),
            "condition_icon": weatherapi["current"].get("condition", {}).get("icon"),
            "air_quality": weatherapi["current"].get("air_quality", {})
        }
    
    if "alerts" in weatherapi and weatherapi["alerts"].get("alert"):
        merged["alerts"] = weatherapi["alerts"]["alert"]
    
    return merged


# ==================== NOWCAST ENDPOINT ====================

@router.get("/nowcast")
async def get_nowcast(
    request: Request,
    latitude: float = Query(..., ge=-90, le=90, description="Latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude"),
    units: WeatherUnits = Query(WeatherUnits.METRIC, description="Temperature units")
):
    """
    Get high-resolution nowcast (0-2 hours) with 15-minute intervals.
    
    Perfect for:
    - Real-time weather tracking
    - Outdoor event planning
    - Delivery/logistics routing
    - Sports/recreation decisions
    """
    metrics = get_metrics()
    metrics.api_requests_total.labels(endpoint="/api/v3/forecast/nowcast", method="GET").inc()
    
    cache_key = f"nowcast:{latitude}:{longitude}:{units}"
    cache = get_cache()
    
    # Check cache (5-minute TTL for nowcast)
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.info(f"Cache hit for nowcast {latitude},{longitude}")
        metrics.cache_hits_total.labels(cache_type="nowcast").inc()
        return JSONResponse(content=cached_data)
    
    metrics.cache_misses_total.labels(cache_type="nowcast").inc()
    
    # Fetch nowcast
    data = fetch_open_meteo_nowcast(latitude, longitude)
    
    if not data:
        raise HTTPException(status_code=503, detail="Unable to fetch nowcast data")
    
    # Build response
    result = {
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "timezone": data.get("timezone"),
        "elevation": data.get("elevation"),
        "nowcast": data.get("minutely_15", {}),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "units": units.value
    }
    
    # Cache for 5 minutes
    cache.set(cache_key, result, ttl=300)
    
    return JSONResponse(content=result)


# ==================== HOURLY FORECAST ENDPOINT ====================

@router.get("/hourly")
async def get_hourly_forecast(
    request: Request,
    latitude: float = Query(..., ge=-90, le=90, description="Latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude"),
    hours: int = Query(48, ge=1, le=168, description="Forecast hours (max 168 = 7 days)"),
    units: WeatherUnits = Query(WeatherUnits.METRIC, description="Temperature units"),
    hybrid: bool = Query(False, description="Include WeatherAPI data for hybrid forecast")
):
    """
    Get hourly weather forecast up to 168 hours (7 days).
    
    Enhanced with:
    - Dew point
    - Wind gusts
    - Visibility
    - Snowfall
    - Pressure trends
    """
    metrics = get_metrics()
    metrics.api_requests_total.labels(endpoint="/api/v3/forecast/hourly", method="GET").inc()
    
    cache_key = f"hourly:{latitude}:{longitude}:{hours}:{units}:{hybrid}"
    cache = get_cache()
    
    # Check cache (30-minute TTL)
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.info(f"Cache hit for hourly {latitude},{longitude}")
        metrics.cache_hits_total.labels(cache_type="hourly").inc()
        return JSONResponse(content=cached_data)
    
    metrics.cache_misses_total.labels(cache_type="hourly").inc()
    
    # Fetch from Open-Meteo
    om_data = fetch_open_meteo_hourly(latitude, longitude, hours)
    
    if not om_data:
        raise HTTPException(status_code=503, detail="Unable to fetch hourly forecast")
    
    # Optionally fetch WeatherAPI for hybrid
    wa_data = None
    if hybrid and settings.ENABLE_FALLBACK:
        wa_data = fetch_weatherapi_forecast(latitude, longitude, days=min(hours // 24 + 1, 14))
    
    # Merge data
    result = merge_forecasts(om_data, wa_data)
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    result["units"] = units.value
    result["source"] = "hybrid" if hybrid and wa_data else "open-meteo"
    
    # Cache for 30 minutes
    cache.set(cache_key, result, ttl=1800)
    
    return JSONResponse(content=result)


# ==================== DAILY FORECAST ENDPOINT ====================

@router.get("/daily")
async def get_daily_forecast(
    request: Request,
    latitude: float = Query(..., ge=-90, le=90, description="Latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude"),
    days: int = Query(7, ge=1, le=16, description="Forecast days (max 16)"),
    units: WeatherUnits = Query(WeatherUnits.METRIC, description="Temperature units"),
    hybrid: bool = Query(False, description="Include WeatherAPI data for hybrid forecast")
):
    """
    Get daily weather forecast up to 16 days.
    
    Enhanced with:
    - Sunrise/sunset times
    - Precipitation hours
    - Max wind gusts
    - UV index max
    - Snowfall accumulation
    """
    metrics = get_metrics()
    metrics.api_requests_total.labels(endpoint="/api/v3/forecast/daily", method="GET").inc()
    
    cache_key = f"daily:{latitude}:{longitude}:{days}:{units}:{hybrid}"
    cache = get_cache()
    
    # Check cache (1-hour TTL)
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.info(f"Cache hit for daily {latitude},{longitude}")
        metrics.cache_hits_total.labels(cache_type="daily").inc()
        return JSONResponse(content=cached_data)
    
    metrics.cache_misses_total.labels(cache_type="daily").inc()
    
    # Fetch from Open-Meteo
    om_data = fetch_open_meteo_daily(latitude, longitude, days)
    
    if not om_data:
        raise HTTPException(status_code=503, detail="Unable to fetch daily forecast")
    
    # Optionally fetch WeatherAPI for hybrid
    wa_data = None
    if hybrid and settings.ENABLE_FALLBACK:
        wa_data = fetch_weatherapi_forecast(latitude, longitude, days=min(days, 14))
    
    # Merge data
    result = merge_forecasts(om_data, wa_data)
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    result["units"] = units.value
    result["source"] = "hybrid" if hybrid and wa_data else "open-meteo"
    
    # Cache for 1 hour
    cache.set(cache_key, result, ttl=3600)
    
    return JSONResponse(content=result)


# ==================== COMBINED FORECAST ENDPOINT ====================

@router.get("/complete")
async def get_complete_forecast(
    request: Request,
    latitude: float = Query(..., ge=-90, le=90, description="Latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude"),
    units: WeatherUnits = Query(WeatherUnits.METRIC, description="Temperature units")
):
    """
    Get complete forecast package:
    - Nowcast (2 hours, 15-min intervals)
    - Hourly (48 hours)
    - Daily (7 days)
    
    One-stop solution for comprehensive weather data.
    """
    metrics = get_metrics()
    metrics.api_requests_total.labels(endpoint="/api/v3/forecast/complete", method="GET").inc()
    
    cache_key = f"complete:{latitude}:{longitude}:{units}"
    cache = get_cache()
    
    # Check cache (15-minute TTL)
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.info(f"Cache hit for complete forecast {latitude},{longitude}")
        metrics.cache_hits_total.labels(cache_type="complete").inc()
        return JSONResponse(content=cached_data)
    
    metrics.cache_misses_total.labels(cache_type="complete").inc()
    
    # Fetch all forecasts in parallel (conceptually - synchronous for simplicity)
    nowcast = fetch_open_meteo_nowcast(latitude, longitude)
    hourly = fetch_open_meteo_hourly(latitude, longitude, 48)
    daily = fetch_open_meteo_daily(latitude, longitude, 7)
    
    if not hourly or not daily:
        raise HTTPException(status_code=503, detail="Unable to fetch complete forecast")
    
    # Build comprehensive response
    result = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": hourly.get("timezone", "UTC"),
        "elevation": hourly.get("elevation"),
        "nowcast": nowcast.get("minutely_15", {}) if nowcast else None,
        "hourly": hourly.get("hourly", {}),
        "daily": daily.get("daily", {}),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "units": units.value
    }
    
    # Cache for 15 minutes
    cache.set(cache_key, result, ttl=900)
    
    return JSONResponse(content=result)
