"""
Weather Alerts Routes

Provides weather alerts and warnings for locations.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

import requests
from fastapi import APIRouter, HTTPException, Query, Request, Depends

from config import settings
from logging_config import get_logger
from cache import get_cache
from metrics import get_metrics
from session_middleware import require_auth
from storage import get_storage
from schemas.alerts import (
    WeatherAlert,
    AlertsResponse,
    AlertSeverity,
    AlertsRefreshResponse
)

logger = get_logger(__name__)

router = APIRouter(
    prefix="/alerts",
    tags=["Weather Alerts"],
    responses={
        400: {"description": "Bad Request"},
        429: {"description": "Rate Limited"},
        503: {"description": "Alerts Service Unavailable"}
    }
)


def _get_weather_alerts(lat: float, lon: float) -> List[WeatherAlert]:
    """
    Fetch weather alerts for a location.
    
    CURRENT IMPLEMENTATION:
    This generates simulated alerts based on current weather conditions
    since Open-Meteo doesn't have a dedicated alerts API.
    
    ALERT GENERATION THRESHOLDS:
    - Thunderstorm: weather_code in [95, 96, 99]
      - Code 99 (severe thunderstorm with hail) = SEVERE severity
      - Codes 95, 96 = MODERATE severity
    
    - High Wind: wind_speed > 60 km/h
      - wind_speed > 90 km/h = SEVERE severity
      - wind_speed > 60 km/h = MODERATE severity
    
    - Heavy Precipitation: precipitation > 10 mm/hour
      - Always MODERATE severity
    
    - Winter Weather: weather_code in [71, 73, 75, 77, 85, 86]
      - Codes 75, 86 (heavy snow) = MODERATE severity
      - Other codes = MINOR severity
    
    FOR PRODUCTION USE:
    Integrate with real alert sources:
    - NWS API (US): https://www.weather.gov/documentation/services-web-api
    - MeteoAlarm (Europe): https://meteoalarm.org/
    - Environment Canada Weather Alerts
    - Japan Meteorological Agency
    
    These provide official government-issued warnings with:
    - Accurate timing (start/end)
    - Affected geographic areas
    - Official severity classifications
    - Detailed instructions
    """
    try:
        # Fetch current weather to generate condition-based alerts
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "weather_code,temperature_2m,wind_speed_10m,precipitation",
            "timezone": "auto"
        }
        
        response = requests.get(
            settings.OPEN_METEO_API_URL,
            params=params,
            timeout=10
        )
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        current = data.get("current", {})
        
        alerts = []
        weather_code = current.get("weather_code", 0)
        wind_speed = current.get("wind_speed_10m", 0)
        precipitation = current.get("precipitation", 0)
        
        # Generate alerts based on conditions
        now = datetime.now(timezone.utc)
        
        # Thunderstorm alerts
        if weather_code in [95, 96, 99]:
            alerts.append(WeatherAlert(
                id=f"alert-{uuid.uuid4().hex[:8]}",
                event="Thunderstorm Warning",
                headline="Thunderstorm activity detected in your area",
                description="A thunderstorm is currently affecting this location. Lightning, heavy rain, and gusty winds are possible.",
                severity=AlertSeverity.SEVERE if weather_code == 99 else AlertSeverity.MODERATE,
                start=now.isoformat(),
                end=(now.replace(hour=now.hour + 3)).isoformat(),
                areas_affected=[f"Area near {lat}, {lon}"],
                sender="IntelliWeather Alerts",
                instruction="Seek shelter indoors and stay away from windows."
            ))
        
        # High wind alerts
        if wind_speed > 60:  # km/h
            severity = AlertSeverity.SEVERE if wind_speed > 90 else AlertSeverity.MODERATE
            alerts.append(WeatherAlert(
                id=f"alert-{uuid.uuid4().hex[:8]}",
                event="High Wind Warning",
                headline=f"High winds of {wind_speed:.0f} km/h expected",
                description=f"Sustained winds of {wind_speed:.0f} km/h are affecting this area. Gusts may be even higher.",
                severity=severity,
                start=now.isoformat(),
                areas_affected=[f"Area near {lat}, {lon}"],
                sender="IntelliWeather Alerts",
                instruction="Secure loose outdoor objects. Avoid unnecessary travel."
            ))
        
        # Heavy precipitation alert
        if precipitation > 10:  # mm/hour
            alerts.append(WeatherAlert(
                id=f"alert-{uuid.uuid4().hex[:8]}",
                event="Heavy Precipitation Warning",
                headline="Heavy precipitation in progress",
                description=f"Precipitation rate of {precipitation:.1f} mm/hour. Flash flooding possible in low-lying areas.",
                severity=AlertSeverity.MODERATE,
                start=now.isoformat(),
                areas_affected=[f"Area near {lat}, {lon}"],
                sender="IntelliWeather Alerts",
                instruction="Avoid flooded roads. Turn around, don't drown."
            ))
        
        # Heavy snow/freezing conditions
        if weather_code in [71, 73, 75, 77, 85, 86]:
            alerts.append(WeatherAlert(
                id=f"alert-{uuid.uuid4().hex[:8]}",
                event="Winter Weather Advisory",
                headline="Snow or winter weather conditions",
                description="Winter weather conditions are affecting this area. Roads may be slippery.",
                severity=AlertSeverity.MODERATE if weather_code in [75, 86] else AlertSeverity.MINOR,
                start=now.isoformat(),
                areas_affected=[f"Area near {lat}, {lon}"],
                sender="IntelliWeather Alerts",
                instruction="Drive with caution. Allow extra travel time."
            ))
        
        return alerts
        
    except Exception as e:
        logger.error(f"Failed to fetch weather alerts: {e}")
        return []


@router.get(
    "",
    response_model=AlertsResponse,
    summary="Get weather alerts for a location",
    description="""
    Get active weather alerts and warnings for a specific location.
    
    **Parameters:**
    - `lat`: Latitude (-90 to 90)
    - `lon`: Longitude (-180 to 180)
    
    **Alert types include:**
    - Thunderstorm warnings
    - High wind warnings
    - Heavy precipitation alerts
    - Winter weather advisories
    
    **Example:**
    ```
    curl "https://api.example.com/alerts?lat=40.7128&lon=-74.006"
    ```
    """
)
async def get_alerts(
    request: Request,
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude")
):
    """Get weather alerts for a location."""
    metrics = get_metrics()
    metrics.increment("total_requests")
    metrics.increment("alerts_requests")
    
    lat_norm = round(lat, 2)
    lon_norm = round(lon, 2)
    
    cache_key = f"alerts:{lat_norm}:{lon_norm}"
    cache = get_cache()
    
    cached = cache.get(cache_key)
    if cached:
        metrics.increment("cache_hits")
        logger.info(f"ALERTS CACHE HIT for {lat_norm}, {lon_norm}")
        return AlertsResponse(**cached)
    
    metrics.increment("cache_misses")
    logger.info(f"ALERTS CACHE MISS for {lat_norm}, {lon_norm}")
    
    alerts = _get_weather_alerts(lat_norm, lon_norm)
    
    result = AlertsResponse(
        latitude=lat_norm,
        longitude=lon_norm,
        location_name=f"Location at {lat_norm}, {lon_norm}",
        alerts=alerts,
        count=len(alerts),
        last_updated=datetime.now(timezone.utc).isoformat(),
        source="live"
    )
    
    # Cache for 15 minutes
    cache.set(cache_key, result.model_dump(), ttl=900)
    
    return result


@router.post(
    "/refresh",
    response_model=AlertsRefreshResponse,
    summary="Manually refresh alerts for popular locations",
    description="Admin endpoint to trigger immediate alert refresh for popular locations."
)
async def refresh_alerts(
    request: Request,
    user = Depends(require_auth)
):
    """Manually refresh alerts for popular locations."""
    metrics = get_metrics()
    metrics.increment("alerts_refresh_requests")
    
    locations = settings.parse_popular_locations()
    cache = get_cache()
    
    total_alerts = 0
    refreshed = 0
    
    for loc in locations:
        lat = loc["lat"]
        lon = loc["lon"]
        
        alerts = _get_weather_alerts(lat, lon)
        total_alerts += len(alerts)
        
        cache_key = f"alerts:{lat}:{lon}"
        result = AlertsResponse(
            latitude=lat,
            longitude=lon,
            location_name=loc["name"],
            alerts=alerts,
            count=len(alerts),
            last_updated=datetime.now(timezone.utc).isoformat(),
            source="refresh"
        )
        
        cache.set(cache_key, result.model_dump(), ttl=900)
        refreshed += 1
    
    logger.info(f"Refreshed alerts for {refreshed} locations, found {total_alerts} alerts")
    
    return AlertsRefreshResponse(
        refreshed_locations=refreshed,
        alerts_found=total_alerts,
        timestamp=datetime.now(timezone.utc).isoformat()
    )
