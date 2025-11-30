"""
Solar & Energy Weather API Routes

Endpoints:
- GET /api/v3/solar/current - Current solar conditions and PV yield
- GET /api/v3/solar/forecast - Daily solar energy forecast
- GET /api/v3/solar/sun-position - Real-time sun position
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime

from modules.solar import (
    get_current_solar_conditions,
    get_daily_solar_forecast,
    calculate_sun_position,
    calculate_daylight_info
)
from cache import get_cache

router = APIRouter(prefix="/api/v3/solar", tags=["Solar & Energy"])


@router.get("/current")
async def current_solar_data(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude coordinate"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude coordinate")
):
    """
    Get current solar radiation and photovoltaic (PV) yield estimates.
    
    Returns:
    - Solar irradiance (GHI, DNI, DHI)
    - Sun position (azimuth, elevation, zenith angle)
    - PV power yield estimates (W/m², kWh/m²/day)
    - Solar potential assessment (excellent to very poor)
    - Daylight information (sunrise, sunset, duration)
    - Temperature derating factors
    
    **Irradiance Types:**
    - **GHI** (Global Horizontal Irradiance): Total solar radiation on horizontal surface
    - **DNI** (Direct Normal Irradiance): Direct sunlight perpendicular to sun
    - **DHI** (Diffuse Horizontal Irradiance): Scattered/diffused sunlight
    
    **PV Yield Assumptions:**
    - Panel efficiency: 20% (modern monocrystalline panels)
    - System losses: 14% (inverter, wiring, soiling, shading)
    - Temperature coefficient: -0.4%/°C above 25°C
    
    **Use Cases:**
    - Solar farm monitoring
    - PV system design and sizing
    - Real-time energy production tracking
    - Solar panel installation planning
    - Energy trading and forecasting
    - Building energy management systems
    """
    
    try:
        # Check cache
        cache = get_cache()
        cache_key = f"solar:current:{latitude:.4f}:{longitude:.4f}"
        
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Fetch current solar conditions
        result = await get_current_solar_conditions(latitude, longitude)
        
        # Cache for 15 minutes (solar data changes gradually)
        if result.get("status") == "success":
            cache.set(cache_key, result, ttl=900)
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch solar conditions: {str(e)}"
        )


@router.get("/forecast")
async def daily_solar_forecast(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude coordinate"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude coordinate"),
    days: int = Query(7, ge=1, le=16, description="Number of forecast days (1-16)"),
):
    """
    Get daily solar energy forecast with PV production estimates.
    
    Returns:
    - Daily total solar radiation (kWh/m²)
    - Sunshine duration (hours)
    - Peak irradiance times
    - Estimated PV yield per day (kWh/m²)
    - Solar potential ratings
    - Sunrise, sunset, and daylight hours
    
    **Daily Energy Estimates:**
    - Total radiation: Sum of all hourly GHI values
    - PV yield: Total radiation × panel efficiency × (1 - system losses)
    - Sunshine duration: Hours with direct sunlight (cloud-adjusted)
    
    **Solar Potential Ratings:**
    - Excellent (80-100): Ideal conditions, >800 W/m² peak, minimal clouds
    - Good (60-79): Favorable conditions, 600-800 W/m² peak
    - Fair (40-59): Moderate conditions, 400-600 W/m² peak
    - Poor (20-39): Limited generation, 200-400 W/m² peak
    - Very Poor (0-19): Minimal generation, <200 W/m² or heavily clouded
    
    **Use Cases:**
    - Multi-day energy production forecasting
    - Grid load balancing
    - Energy storage scheduling
    - Solar farm operations planning
    - Energy market bidding
    - Maintenance scheduling (during low production days)
    """
    
    try:
        # Check cache
        cache = get_cache()
        cache_key = f"solar:forecast:{latitude:.4f}:{longitude:.4f}:{days}"
        
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Fetch forecast
        result = await get_daily_solar_forecast(latitude, longitude, days)
        
        # Cache for 6 hours
        if result.get("status") == "success":
            cache.set(cache_key, result, ttl=21600)
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch solar forecast: {str(e)}"
        )


@router.get("/sun-position")
async def sun_position(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude coordinate"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude coordinate"),
    timestamp: Optional[str] = Query(None, description="ISO timestamp (UTC), defaults to now"),
):
    """
    Get sun position (azimuth and elevation) for specific location and time.
    
    Returns:
    - Solar azimuth angle (degrees, 0=North, 90=East, 180=South, 270=West)
    - Solar elevation angle (degrees, 0=horizon, 90=zenith)
    - Zenith angle (degrees from directly overhead)
    - Daylight status (is it daytime?)
    - Direct sun visibility (sun above horizon?)
    
    **Angles Explained:**
    - **Azimuth**: Compass direction of the sun (0-360°)
    - **Elevation**: Height of sun above horizon (-90 to +90°)
    - **Zenith**: Angle from directly overhead (0-180°)
    
    **Daylight Conditions:**
    - Direct sun: Elevation > 0° (sun visible above horizon)
    - Civil twilight: Elevation > -6° (sufficient light for outdoor activities)
    - Nautical twilight: Elevation > -12°
    - Astronomical twilight: Elevation > -18°
    - Night: Elevation < -18°
    
    **Use Cases:**
    - Solar panel orientation optimization
    - Building shading analysis
    - Photography (golden hour, blue hour planning)
    - Architecture and urban planning
    - Agricultural planning (sun exposure for crops)
    - Satellite tracking and communications
    """
    
    try:
        # Parse timestamp or use current time
        if timestamp:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=None)
            dt = dt.replace(tzinfo=None)  # Work with naive UTC datetime
        else:
            dt = datetime.utcnow()
        
        # Calculate sun position
        sun_pos = calculate_sun_position(latitude, longitude, dt)
        
        # Get daylight info for today
        daylight = calculate_daylight_info(latitude, longitude, dt.date())
        
        result = {
            "status": "success",
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": dt.isoformat() + "Z",
            "sun_position": sun_pos,
            "daylight_info": daylight
        }
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate sun position: {str(e)}"
        )


@router.get("/health")
async def solar_api_health():
    """
    Health check endpoint for solar API.
    
    Returns API status and capabilities.
    """
    
    return {
        "status": "operational",
        "service": "Solar & Energy Weather API",
        "version": "1.0.0",
        "data_sources": [
            "Open-Meteo Weather API"
        ],
        "features": [
            "Solar irradiance (GHI, DNI, DHI)",
            "PV yield estimation",
            "Sun position calculation",
            "Daylight prediction",
            "Solar potential assessment"
        ],
        "irradiance_metrics": [
            "Global Horizontal Irradiance (GHI)",
            "Direct Normal Irradiance (DNI)",
            "Diffuse Horizontal Irradiance (DHI)"
        ],
        "forecast_range": "16 days",
        "pv_assumptions": {
            "panel_efficiency": "20%",
            "system_losses": "14%",
            "temperature_coefficient": "-0.4%/°C"
        },
        "timestamp": datetime.utcnow().isoformat()
    }
