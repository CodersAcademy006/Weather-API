"""
Pollen Forecast API Routes

Endpoints:
- GET /api/v3/pollen/current - Current pollen levels and allergy risk
- GET /api/v3/pollen/forecast - Daily pollen forecast (up to 7 days)
- GET /api/v3/pollen/trends - Pollen trends and seasonal analysis
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime

from modules.pollen import (
    get_current_pollen,
    get_daily_pollen_forecast,
    get_pollen_trends
)
from cache import get_cache

router = APIRouter(prefix="/api/v3/pollen", tags=["Pollen Forecast"])


@router.get("/current")
async def current_pollen_levels(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude coordinate"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude coordinate")
):
    """
    Get current pollen levels and allergy risk assessment.
    
    Returns:
    - Current pollen levels for tree, grass, and weed
    - Species breakdown (alder, birch, olive, grass, mugwort, ragweed)
    - Allergy risk level (minimal, low, moderate, high, severe)
    - Recommendations and precautions
    - Suggested activities
    
    **Pollen Score Scale (0-100):**
    - 0-10: None/Minimal risk
    - 10-30: Low risk
    - 30-60: Moderate risk
    - 60-80: High risk
    - 80-100: Severe risk
    
    **Use Cases:**
    - Health & fitness apps
    - Allergy tracking applications
    - Outdoor activity planning
    - Air purifier automation
    """
    
    try:
        # Fetch current pollen data
        result = await get_current_pollen(latitude, longitude)
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch pollen data: {str(e)}"
        )


@router.get("/forecast")
async def daily_pollen_forecast(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude coordinate"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude coordinate"),
    days: int = Query(7, ge=1, le=7, description="Number of forecast days"),
):
    """
    Get daily pollen forecast with peak hours and best times for outdoor activities.
    
    Returns:
    - Daily pollen forecasts (up to 7 days)
    - Peak pollen hours each day
    - Best hours for outdoor activities (lowest pollen)
    - Daily allergy risk assessments
    - Recommendations per day
    
    **Features:**
    - Peak hour identification
    - Best activity hours (lowest pollen)
    - Daily risk levels
    - Species-specific breakdown
    - Trend indicators
    
    **Use Cases:**
    - Weekly allergy planning
    - Outdoor event scheduling
    - Exercise timing optimization
    - Medication scheduling
    """
    
    try:
        # Check cache
        cache = get_cache()
        cache_key = f"pollen:forecast:{latitude:.4f}:{longitude:.4f}:{days}"
        
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Fetch forecast
        result = await get_daily_pollen_forecast(latitude, longitude, days)
        
        # Cache for 6 hours
        if result.get("status") == "success":
            cache.set(cache_key, result, ttl=21600)
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch pollen forecast: {str(e)}"
        )


@router.get("/trends")
async def pollen_trends_analysis(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude coordinate"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude coordinate"),
):
    """
    Get pollen trends and seasonal analysis.
    
    Returns:
    - 7-day trend direction (increasing, decreasing, stable)
    - Current season information
    - Dominant pollen type for season
    - Forecast summary (average, peak day, best day)
    - Historical context
    
    **Trend Analysis:**
    - Direction: Increasing, decreasing, or stable
    - Score progression over 7 days
    - Season-specific insights
    - Peak and best days identification
    
    **Seasonal Information:**
    - Spring: Tree pollen dominant (birch, alder, olive)
    - Summer: Grass pollen dominant
    - Fall: Weed pollen dominant (ragweed, mugwort)
    - Winter: Lowest pollen levels
    
    **Use Cases:**
    - Long-term allergy planning
    - Seasonal preparation
    - Medication planning
    - Relocation decisions
    """
    
    try:
        # Check cache
        cache = get_cache()
        cache_key = f"pollen:trends:{latitude:.4f}:{longitude:.4f}"
        
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Fetch trends
        result = await get_pollen_trends(latitude, longitude)
        
        # Cache for 12 hours
        if result.get("status") == "success":
            cache.set(cache_key, result, ttl=43200)
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch pollen trends: {str(e)}"
        )


@router.get("/health")
async def pollen_api_health():
    """
    Health check endpoint for pollen API.
    
    Returns API status and data source information.
    """
    
    return {
        "status": "operational",
        "service": "Pollen Forecast API",
        "version": "1.0.0",
        "data_sources": [
            "Open-Meteo Air Quality API"
        ],
        "supported_species": [
            "alder",
            "birch",
            "olive",
            "grass",
            "mugwort",
            "ragweed"
        ],
        "forecast_range": "7 days",
        "update_frequency": "hourly",
        "timestamp": datetime.utcnow().isoformat()
    }
