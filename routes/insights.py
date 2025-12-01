"""
Weather Insights Routes - Proprietary Weather Intelligence

Provides calculated weather insights beyond raw API data:
- Heat index & wind chill
- Fire risk scoring
- UV exposure assessments
- Travel disruption predictions
- Comfort indices
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from config import settings
from logging_config import get_logger
from cache import get_cache
from metrics import get_metrics
from modules.weather_insights import (
    calculate_heat_index,
    calculate_wind_chill,
    calculate_wet_bulb_temperature,
    calculate_fire_risk_score,
    calculate_uv_exposure_score,
    calculate_travel_disruption_risk,
    calculate_rain_confidence,
    calculate_comfort_index,
    calculate_all_insights
)
import requests

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v3/insights", tags=["Weather Insights"])


def fetch_current_weather(lat: float, lon: float) -> dict:
    """Fetch current weather data for insights calculation."""
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "precipitation",
                "weather_code",
                "wind_speed_10m",
                "wind_direction_10m",
                "pressure_msl",
                "cloud_cover",
                "visibility",
                "uv_index"
            ],
            "timezone": "auto"
        }
        
        response = requests.get(
            settings.OPEN_METEO_API_URL,
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to fetch weather data: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching weather data: {e}")
        return None


@router.get("/current")
async def get_current_insights(
    request: Request,
    latitude: float = Query(..., ge=-90, le=90, description="Latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude")
):
    """
    Get comprehensive weather insights for current conditions.
    
    Returns all calculated metrics:
    - Heat index / wind chill
    - Wet bulb temperature
    - Fire risk score
    - UV exposure assessment
    - Travel disruption risk
    - Comfort index
    """
    metrics = get_metrics()
    metrics.increment("total_requests")
    
    cache_key = f"insights:current:{latitude}:{longitude}"
    cache = get_cache()
    
    # Check cache (15-minute TTL)
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.info(f"Cache hit for insights {latitude},{longitude}")
        metrics.increment("cache_hits")
        return JSONResponse(content=cached_data)
    
    metrics.increment("cache_misses")
    
    # Fetch current weather
    weather_data = fetch_current_weather(latitude, longitude)
    
    if not weather_data or "current" not in weather_data:
        raise HTTPException(status_code=503, detail="Unable to fetch weather data for insights")
    
    current = weather_data["current"]
    
    # Calculate all insights
    insights = calculate_all_insights(current)
    
    # Build response
    result = {
        "latitude": weather_data.get("latitude"),
        "longitude": weather_data.get("longitude"),
        "timezone": weather_data.get("timezone"),
        "elevation": weather_data.get("elevation"),
        "timestamp": current.get("time"),
        "raw_data": current,
        "insights": insights,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Cache for 15 minutes
    cache.set(cache_key, result, ttl=900)
    
    return JSONResponse(content=result)


@router.get("/fire-risk")
async def get_fire_risk(
    request: Request,
    latitude: float = Query(..., ge=-90, le=90, description="Latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude"),
    days_since_rain: int = Query(0, ge=0, le=365, description="Days since last significant rain")
):
    """
    Get detailed fire risk assessment for a location.
    
    Considers:
    - Temperature
    - Humidity
    - Wind speed
    - Recent precipitation
    - Days since rain
    
    Returns risk score 0-100 with category and recommendations.
    """
    metrics = get_metrics()
    metrics.increment("total_requests")
    
    # Fetch current weather
    weather_data = fetch_current_weather(latitude, longitude)
    
    if not weather_data or "current" not in weather_data:
        raise HTTPException(status_code=503, detail="Unable to fetch weather data")
    
    current = weather_data["current"]
    
    fire_risk = calculate_fire_risk_score(
        temp_c=current.get("temperature_2m", 20),
        humidity=current.get("relative_humidity_2m", 50),
        wind_speed_kmh=current.get("wind_speed_10m", 0),
        precipitation_mm=current.get("precipitation", 0),
        days_since_rain=days_since_rain
    )
    
    return JSONResponse(content={
        "latitude": weather_data.get("latitude"),
        "longitude": weather_data.get("longitude"),
        "timestamp": current.get("time"),
        "fire_risk": fire_risk,
        "conditions": {
            "temperature_c": current.get("temperature_2m"),
            "humidity_percent": current.get("relative_humidity_2m"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "precipitation_mm": current.get("precipitation"),
            "days_since_rain": days_since_rain
        }
    })


@router.get("/uv-exposure")
async def get_uv_exposure(
    request: Request,
    latitude: float = Query(..., ge=-90, le=90, description="Latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude")
):
    """
    Get detailed UV exposure assessment and protection recommendations.
    
    Considers:
    - UV index
    - Cloud cover (reduces UV exposure)
    - Time of day
    
    Returns protection recommendations and burn time estimates.
    """
    metrics = get_metrics()
    metrics.increment("total_requests")
    
    # Fetch current weather
    weather_data = fetch_current_weather(latitude, longitude)
    
    if not weather_data or "current" not in weather_data:
        raise HTTPException(status_code=503, detail="Unable to fetch weather data")
    
    current = weather_data["current"]
    
    uv_exposure = calculate_uv_exposure_score(
        uv_index=current.get("uv_index", 0),
        cloud_cover=current.get("cloud_cover", 0)
    )
    
    return JSONResponse(content={
        "latitude": weather_data.get("latitude"),
        "longitude": weather_data.get("longitude"),
        "timestamp": current.get("time"),
        "uv_exposure": uv_exposure,
        "conditions": {
            "uv_index": current.get("uv_index"),
            "cloud_cover_percent": current.get("cloud_cover")
        }
    })


@router.get("/travel-disruption")
async def get_travel_disruption(
    request: Request,
    latitude: float = Query(..., ge=-90, le=90, description="Latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude")
):
    """
    Get travel disruption risk assessment for all transport modes.
    
    Analyzes impact on:
    - Road transport
    - Rail
    - Aviation
    - Maritime
    
    Considers weather, visibility, wind, and precipitation.
    """
    metrics = get_metrics()
    metrics.increment("total_requests")
    
    # Fetch current weather
    weather_data = fetch_current_weather(latitude, longitude)
    
    if not weather_data or "current" not in weather_data:
        raise HTTPException(status_code=503, detail="Unable to fetch weather data")
    
    current = weather_data["current"]
    
    disruption = calculate_travel_disruption_risk(
        precipitation_mm=current.get("precipitation", 0),
        wind_speed_kmh=current.get("wind_speed_10m", 0),
        visibility_m=current.get("visibility", 10000),
        temp_c=current.get("temperature_2m", 20),
        weather_code=current.get("weather_code", 0)
    )
    
    return JSONResponse(content={
        "latitude": weather_data.get("latitude"),
        "longitude": weather_data.get("longitude"),
        "timestamp": current.get("time"),
        "travel_disruption": disruption,
        "conditions": {
            "precipitation_mm": current.get("precipitation"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "visibility_m": current.get("visibility"),
            "temperature_c": current.get("temperature_2m"),
            "weather_code": current.get("weather_code")
        }
    })


@router.get("/comfort")
async def get_comfort_index(
    request: Request,
    latitude: float = Query(..., ge=-90, le=90, description="Latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude")
):
    """
    Get overall comfort index for outdoor activities.
    
    Combines:
    - Temperature
    - Humidity
    - Wind
    
    Returns comfort score 0-100 with category and description.
    Perfect for event planning and outdoor activity recommendations.
    """
    metrics = get_metrics()
    metrics.increment("total_requests")
    
    # Fetch current weather
    weather_data = fetch_current_weather(latitude, longitude)
    
    if not weather_data or "current" not in weather_data:
        raise HTTPException(status_code=503, detail="Unable to fetch weather data")
    
    current = weather_data["current"]
    
    comfort = calculate_comfort_index(
        temp_c=current.get("temperature_2m", 20),
        humidity=current.get("relative_humidity_2m", 50),
        wind_speed_kmh=current.get("wind_speed_10m", 0)
    )
    
    return JSONResponse(content={
        "latitude": weather_data.get("latitude"),
        "longitude": weather_data.get("longitude"),
        "timestamp": current.get("time"),
        "comfort": comfort,
        "conditions": {
            "temperature_c": current.get("temperature_2m"),
            "humidity_percent": current.get("relative_humidity_2m"),
            "wind_speed_kmh": current.get("wind_speed_10m")
        }
    })


@router.get("/feels-like")
async def get_feels_like_temperature(
    request: Request,
    latitude: float = Query(..., ge=-90, le=90, description="Latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude")
):
    """
    Get comprehensive feels-like temperature analysis.
    
    Returns:
    - Heat index (hot conditions)
    - Wind chill (cold conditions)
    - Wet bulb temperature (heat stress)
    - Actual temperature
    
    Helps users understand what the weather actually feels like.
    """
    metrics = get_metrics()
    metrics.increment("total_requests")
    
    # Fetch current weather
    weather_data = fetch_current_weather(latitude, longitude)
    
    if not weather_data or "current" not in weather_data:
        raise HTTPException(status_code=503, detail="Unable to fetch weather data")
    
    current = weather_data["current"]
    
    temp = current.get("temperature_2m", 20)
    humidity = current.get("relative_humidity_2m", 50)
    wind_speed = current.get("wind_speed_10m", 0)
    pressure = current.get("pressure_msl", 1013.25)
    
    result = {
        "latitude": weather_data.get("latitude"),
        "longitude": weather_data.get("longitude"),
        "timestamp": current.get("time"),
        "actual_temperature_c": temp,
        "wet_bulb_temperature_c": round(calculate_wet_bulb_temperature(temp, humidity, pressure), 1)
    }
    
    # Add heat index if hot
    if temp > 27:
        result["heat_index_c"] = round(calculate_heat_index(temp, humidity), 1)
        result["dominant_factor"] = "heat"
    
    # Add wind chill if cold and windy
    if temp < 10 and wind_speed > 4.8:
        result["wind_chill_c"] = round(calculate_wind_chill(temp, wind_speed), 1)
        result["dominant_factor"] = "cold"
    
    if "heat_index_c" not in result and "wind_chill_c" not in result:
        result["dominant_factor"] = "neutral"
        result["feels_like_c"] = temp
    elif "heat_index_c" in result:
        result["feels_like_c"] = result["heat_index_c"]
    else:
        result["feels_like_c"] = result["wind_chill_c"]
    
    result["conditions"] = {
        "temperature_c": temp,
        "humidity_percent": humidity,
        "wind_speed_kmh": wind_speed,
        "pressure_hpa": pressure
    }
    
    return JSONResponse(content=result)
