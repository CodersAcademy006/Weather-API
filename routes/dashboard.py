from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
import asyncio
from datetime import datetime
from typing import Optional
import hashlib

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# In-memory cache for user locations (session-based)
user_location_cache = {}

def get_session_id(request: Request) -> Optional[str]:
    """Extract session ID from request"""
    session_cookie = request.cookies.get("session_id")
    return session_cookie

def cache_key(session_id: str) -> str:
    """Generate cache key for session"""
    return hashlib.sha256(session_id.encode()).hexdigest()

@router.post("/location/set")
async def set_user_location(
    request: Request,
    location: dict
):
    """Cache user's selected location"""
    session_id = get_session_id(request)
    key = cache_key(session_id)
    
    user_location_cache[key] = {
        "location": location.get("location"),
        "lat": location.get("lat"),
        "lon": location.get("lon"),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return {"status": "cached", "location": location.get("location")}

@router.get("/location/get")
async def get_user_location(request: Request):
    """Retrieve cached user location"""
    session_id = get_session_id(request)
    if not session_id:
        return {"cached": False}
    
    key = cache_key(session_id)
    
    cached = user_location_cache.get(key)
    if not cached:
        return {"cached": False}
    
    return {"cached": True, **cached}

@router.delete("/location/clear")
async def clear_user_location(request: Request):
    """Clear user location cache on exit"""
    session_id = get_session_id(request)
    if not session_id:
        return {"status": "no_session"}
    
    key = cache_key(session_id)
    
    if key in user_location_cache:
        del user_location_cache[key]
        return {"status": "cleared"}
    
    return {"status": "not_found"}

@router.get("/weather/current")
async def get_current_weather(
    request: Request,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    location: Optional[str] = None
):
    """Get current weather for user location"""
    
    # Use provided coords or fetch from cache
    if not lat or not lon:
        session_id = get_session_id(request)
        if session_id:
            key = cache_key(session_id)
            cached = user_location_cache.get(key)
            
            if cached:
                lat = cached["lat"]
                lon = cached["lon"]
                location = cached["location"] if not location else location
        
        if (not lat or not lon) and location:
            # Geocode the location using the geocoding service
            from modules.geocode import GeocodingService
            geocoder = GeocodingService()
            geo_result = geocoder.search(location, limit=1)
            
            if geo_result.get("results"):
                result = geo_result["results"][0]
                lat = result["latitude"]
                lon = result["longitude"]
            else:
                raise HTTPException(status_code=400, detail="Location not found")
        
        if not lat or not lon:
            raise HTTPException(status_code=400, detail="No location provided or cached")
    
    # Set default location if still not set
    if not location:
        location = f"{lat:.4f}, {lon:.4f}"
    
    # Fetch weather data using Open-Meteo API directly
    import httpx
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            params = {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
                "timezone": "auto"
            }
            response = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params=params
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to fetch weather data")
            
            weather_data = response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Weather API timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Weather API error: {str(e)}")
    
    return {
        "location": location or f"{lat},{lon}",
        "lat": lat,
        "lon": lon,
        "weather": weather_data,
        "timestamp": datetime.utcnow().isoformat()
    }
