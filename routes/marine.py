"""
Marine & Coastal Weather API Routes

Endpoints:
- GET /api/v3/marine/current - Current marine conditions
- GET /api/v3/marine/forecast - Daily marine forecast
- GET /api/v3/marine/tides - Tide predictions
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime, timedelta

from modules.marine import (
    get_current_marine_conditions,
    get_marine_forecast,
    calculate_tide_approximation
)
from cache import get_cache

router = APIRouter(prefix="/api/v3/marine", tags=["Marine Weather"])


@router.get("/current")
async def current_marine_conditions(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude coordinate"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude coordinate")
):
    """
    Get current marine and coastal weather conditions.
    
    Returns:
    - Wave height, direction, and period
    - Swell conditions
    - Wind wave conditions
    - Ocean current velocity and direction
    - Sea state classification (WMO code)
    - Approximate tide information
    - Activity risk assessment (swimming, surfing, sailing, fishing, diving)
    
    **Wave Height Classification (WMO Sea State):**
    - 0: Calm (0-0.1m)
    - 1: Smooth (0.1-0.5m)
    - 2: Slight (0.5-1.25m)
    - 3: Moderate (1.25-2.5m)
    - 4: Rough (2.5-4m)
    - 5: Very Rough (4-6m)
    - 6: High (6-9m)
    - 7: Very High (9-14m)
    - 8: Phenomenal (14m+)
    
    **Use Cases:**
    - Marine navigation
    - Surfing/water sports planning
    - Fishing trip planning
    - Shipping & logistics
    - Beach safety assessment
    - Tourism applications
    """
    
    try:
        # Check cache
        cache = get_cache()
        cache_key = f"marine:current:{latitude:.4f}:{longitude:.4f}"
        
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Fetch marine conditions
        result = await get_current_marine_conditions(latitude, longitude)
        
        # Cache for 30 minutes
        if result.get("status") == "success":
            cache.set(cache_key, result, ttl=1800)
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch marine conditions: {str(e)}"
        )


@router.get("/forecast")
async def marine_forecast(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude coordinate"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude coordinate"),
    days: int = Query(7, ge=1, le=7, description="Number of forecast days"),
):
    """
    Get daily marine weather forecast.
    
    Returns:
    - Daily maximum wave heights
    - Dominant wave direction
    - Maximum wave period
    - Sea state classifications
    - Activity risk assessments per day
    
    **Features:**
    - Up to 7-day forecast
    - Daily peak conditions
    - Activity planning guidance
    - Sea state evolution
    
    **Use Cases:**
    - Multi-day marine voyage planning
    - Fishing expedition scheduling
    - Sailing regatta planning
    - Marine construction scheduling
    - Offshore operations planning
    """
    
    try:
        # Check cache
        cache = get_cache()
        cache_key = f"marine:forecast:{latitude:.4f}:{longitude:.4f}:{days}"
        
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Fetch forecast
        result = await get_marine_forecast(latitude, longitude, days)
        
        # Cache for 6 hours
        if result.get("status") == "success":
            cache.set(cache_key, result, ttl=21600)
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch marine forecast: {str(e)}"
        )


@router.get("/tides")
async def tide_predictions(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude coordinate"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude coordinate"),
    hours: int = Query(24, ge=1, le=168, description="Number of hours to forecast"),
):
    """
    Get approximate tide predictions based on astronomical calculations.
    
    Returns:
    - Tide state (high, low, rising, falling)
    - Tide type (spring, neap, normal)
    - Lunar phase
    - Time until next tide change
    - Tidal range factor
    
    **Important Notes:**
    - These are approximate astronomical tide predictions
    - Does NOT account for local geography, weather, or bathymetry
    - For navigation, use official tide tables (NOAA, local authorities)
    
    **Tide Types:**
    - **Spring Tides**: Higher high tides and lower low tides (new/full moon)
    - **Neap Tides**: Lower high tides and higher low tides (quarter moons)
    - **Normal Tides**: Between spring and neap
    
    **Use Cases:**
    - General tide awareness
    - Beachcombing planning
    - Coastal photography
    - Educational purposes
    - Preliminary planning (verify with official sources)
    """
    
    try:
        # Check cache
        cache = get_cache()
        now = datetime.utcnow()
        cache_key = f"tides:{latitude:.4f}:{longitude:.4f}:{now.hour}"
        
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Generate hourly tide predictions
        predictions = []
        
        for hour_offset in range(hours):
            prediction_time = now + timedelta(hours=hour_offset)
            tide_info = calculate_tide_approximation(latitude, longitude, prediction_time)
            
            predictions.append({
                "timestamp": prediction_time.isoformat() + "Z",
                **tide_info
            })
        
        result = {
            "status": "success",
            "latitude": latitude,
            "longitude": longitude,
            "predictions": predictions,
            "note": "Approximate astronomical tide predictions. Use official tide tables for navigation.",
            "metadata": {
                "calculation_method": "Astronomical (lunar position)",
                "accuracy": "Approximate - does not account for local geography"
            }
        }
        
        # Cache for 1 hour
        cache.set(cache_key, result, ttl=3600)
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate tide predictions: {str(e)}"
        )


@router.get("/health")
async def marine_api_health():
    """
    Health check endpoint for marine API.
    
    Returns API status and data source information.
    """
    
    return {
        "status": "operational",
        "service": "Marine & Coastal Weather API",
        "version": "1.0.0",
        "data_sources": [
            "Open-Meteo Marine Weather API"
        ],
        "features": [
            "Wave height and swell",
            "Ocean currents",
            "Sea state classification",
            "Astronomical tide predictions",
            "Activity risk assessment"
        ],
        "supported_activities": [
            "swimming",
            "surfing",
            "sailing",
            "fishing",
            "diving"
        ],
        "forecast_range": "7 days",
        "timestamp": datetime.utcnow().isoformat()
    }
