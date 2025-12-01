"""
Extended Air Quality API Routes (AQI V2)

Endpoints:
- GET /api/v3/air-quality/current - Current air quality with all pollutants
- GET /api/v3/air-quality/forecast - Daily air quality forecast
- GET /api/v3/air-quality/pollutant/{name} - Specific pollutant information
"""

from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional
from datetime import datetime

from modules.air_quality import (
    get_current_air_quality,
    get_air_quality_forecast,
    get_pollutant_health_impact
)
from cache import get_cache

router = APIRouter(prefix="/api/v3/air-quality", tags=["Air Quality (AQI V2)"])


@router.get("/current")
async def current_air_quality(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude coordinate"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude coordinate")
):
    """
    Get current comprehensive air quality data with detailed pollutant breakdown.
    
    Returns:
    - **US EPA AQI** (0-500 scale)
    - **European AQI** (1-6 scale)
    - **Detailed Pollutants:**
      - PM1 (Ultrafine particles)
      - PM2.5 (Fine particles)
      - PM10 (Coarse particles)
      - NO₂ (Nitrogen dioxide)
      - SO₂ (Sulfur dioxide)
      - CO (Carbon monoxide)
      - O₃ (Ground-level ozone)
    - Individual pollutant AQI values
    - Health impacts per pollutant
    - Health guidance for general population and sensitive groups
    - Outdoor activity recommendations
    - UV Index
    
    **US EPA AQI Levels:**
    - 0-50: Good (Green)
    - 51-100: Moderate (Yellow)
    - 101-150: Unhealthy for Sensitive Groups (Orange)
    - 151-200: Unhealthy (Red)
    - 201-300: Very Unhealthy (Purple)
    - 301-500: Hazardous (Maroon)
    
    **Sensitive Groups Include:**
    - People with asthma or respiratory diseases
    - People with heart disease
    - Children and teenagers
    - Older adults
    - People who are active outdoors
    
    **Use Cases:**
    - Health & fitness apps
    - Air purifier automation
    - Outdoor activity planning
    - Asthma/allergy management
    - Public health monitoring
    - Smart city applications
    - HVAC system control
    """
    
    try:
        # Check cache
        cache = get_cache()
        cache_key = f"aqi:current:{latitude:.4f}:{longitude:.4f}"
        
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Fetch current air quality
        result = await get_current_air_quality(latitude, longitude)
        
        # Cache for 1 hour
        if result.get("status") == "success":
            cache.set(cache_key, result, ttl=3600)
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch air quality data: {str(e)}"
        )


@router.get("/forecast")
async def air_quality_forecast(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude coordinate"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude coordinate"),
    days: int = Query(7, ge=1, le=7, description="Number of forecast days"),
):
    """
    Get daily air quality forecast with pollutant predictions.
    
    Returns:
    - Daily AQI forecasts (up to 7 days)
    - Maximum pollutant concentrations per day
    - Daily health guidance
    - Outdoor activity recommendations
    - UV Index forecasts
    
    **Features:**
    - Worst-case pollutant levels per day
    - Day-by-day health impact assessment
    - Planning guidance for outdoor activities
    - Multi-day air quality trends
    
    **Use Cases:**
    - Weekly health planning
    - Outdoor event scheduling
    - Exercise planning for respiratory patients
    - Air purifier scheduling
    - HVAC system pre-planning
    - Public health advisories
    """
    
    try:
        # Check cache
        cache = get_cache()
        cache_key = f"aqi:forecast:{latitude:.4f}:{longitude:.4f}:{days}"
        
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Fetch forecast
        result = await get_air_quality_forecast(latitude, longitude, days)
        
        # Cache for 6 hours
        if result.get("status") == "success":
            cache.set(cache_key, result, ttl=21600)
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch air quality forecast: {str(e)}"
        )


@router.get("/pollutant/{pollutant_name}")
async def pollutant_information(
    pollutant_name: str = Path(..., description="Pollutant name (pm25, pm10, no2, so2, co, o3)"),
):
    """
    Get detailed information about a specific air pollutant.
    
    Returns:
    - Pollutant full name and description
    - Particle size (for particulate matter)
    - Common sources
    - Health effects
    - Special notes and warnings
    
    **Supported Pollutants:**
    - **pm25**: Fine Particulate Matter (PM2.5)
    - **pm10**: Coarse Particulate Matter (PM10)
    - **no2**: Nitrogen Dioxide
    - **so2**: Sulfur Dioxide
    - **co**: Carbon Monoxide
    - **o3**: Ground-level Ozone
    
    **Use Cases:**
    - Educational applications
    - Health awareness campaigns
    - Environmental education
    - Air quality reporting systems
    """
    
    try:
        pollutant_lower = pollutant_name.lower()
        
        # Get pollutant information
        info = get_pollutant_health_impact(pollutant_lower, 0)
        
        if "name" not in info or info["name"] == pollutant_name.upper():
            raise HTTPException(
                status_code=404,
                detail=f"Pollutant '{pollutant_name}' not found. Supported: pm25, pm10, no2, so2, co, o3"
            )
        
        return {
            "status": "success",
            "pollutant": pollutant_lower,
            "information": info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch pollutant information: {str(e)}"
        )


@router.get("/health")
async def air_quality_api_health():
    """
    Health check endpoint for air quality API.
    
    Returns API status and capabilities.
    """
    
    return {
        "status": "operational",
        "service": "Extended Air Quality API (AQI V2)",
        "version": "2.0.0",
        "data_sources": [
            "Open-Meteo Air Quality API"
        ],
        "supported_pollutants": [
            "PM2.5 (Fine Particulate Matter)",
            "PM10 (Coarse Particulate Matter)",
            "NO₂ (Nitrogen Dioxide)",
            "SO₂ (Sulfur Dioxide)",
            "CO (Carbon Monoxide)",
            "O₃ (Ground-level Ozone)",
            "Dust",
            "UV Index"
        ],
        "aqi_standards": [
            "US EPA AQI (0-500)",
            "European EAQI (1-6)"
        ],
        "features": [
            "Real-time pollutant monitoring",
            "Individual pollutant AQI calculations",
            "Health impact assessments",
            "Sensitive group warnings",
            "Outdoor activity guidance",
            "7-day air quality forecast"
        ],
        "update_frequency": "hourly",
        "timestamp": datetime.utcnow().isoformat()
    }
