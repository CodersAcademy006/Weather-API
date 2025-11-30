"""
Geocoding Routes V2 - Enhanced with Autocomplete

Provides geocoding, reverse geocoding, and autocomplete endpoints.
Enhanced for LEVEL 1 feature requirements.
"""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from typing import List, Optional

from config import settings
from logging_config import get_logger
from metrics import get_metrics
from modules.geocode import get_geocoding_service
from schemas.geocode import (
    GeocodeSearchResponse,
    ReverseGeocodeResponse,
    GeoLocation
)
from cache import get_cache

logger = get_logger(__name__)

router = APIRouter(
    prefix="/geocode",
    tags=["Geocoding"],
    responses={
        400: {"description": "Bad Request"},
        429: {"description": "Rate Limited"},
        503: {"description": "Geocoding Service Unavailable"}
    }
)


@router.get(
    "/search",
    response_model=GeocodeSearchResponse,
    summary="Search for locations by name",
    description="""
    Search for locations by city name, place name, or other geographic identifiers.
    
    **Parameters:**
    - `q`: Search query (city name, etc.)
    - `limit`: Maximum results (1-20, default 5)
    - `lang`: Language for results (optional)
    
    **Example:**
    ```
    curl "https://api.example.com/geocode/search?q=New York&limit=5"
    ```
    
    **Response includes:**
    - Location name
    - Coordinates (latitude, longitude)
    - Country and administrative regions
    - Timezone
    - Population (when available)
    """
)
async def search_locations(
    request: Request,
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    limit: int = Query(5, ge=1, le=20, description="Maximum results"),
    lang: str = Query(None, description="Language code (en, hi, ar, etc.)")
):
    """Search for locations by name."""
    metrics = get_metrics()
    metrics.increment("total_requests")
    metrics.increment("geocode_search_requests")
    
    geocoding = get_geocoding_service()
    result = geocoding.search(q, limit, lang)
    
    if result.get("source") == "error":
        raise HTTPException(
            status_code=503,
            detail="Geocoding service temporarily unavailable"
        )
    
    # Convert to response model
    locations = [
        GeoLocation(**loc) for loc in result.get("results", [])
    ]
    
    return GeocodeSearchResponse(
        results=locations,
        query=result.get("query", q),
        count=len(locations),
        source=result.get("source", "live")
    )


@router.get(
    "/reverse",
    response_model=ReverseGeocodeResponse,
    summary="Reverse geocode coordinates",
    description="""
    Get location information for a set of coordinates.
    
    **Parameters:**
    - `lat`: Latitude (-90 to 90)
    - `lon`: Longitude (-180 to 180)
    
    **Example:**
    ```
    curl "https://api.example.com/geocode/reverse?lat=40.7128&lon=-74.006"
    ```
    """
)
async def reverse_geocode(
    request: Request,
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude")
):
    """Reverse geocode coordinates to location information."""
    metrics = get_metrics()
    metrics.increment("total_requests")
    metrics.increment("geocode_reverse_requests")
    
    geocoding = get_geocoding_service()
    result = geocoding.reverse(lat, lon)
    
    if result.get("source") == "error":
        raise HTTPException(
            status_code=503,
            detail="Geocoding service temporarily unavailable"
        )
    
    location = None
    if result.get("location"):
        location = GeoLocation(**result["location"])
    
    return ReverseGeocodeResponse(
        location=location,
        latitude=result.get("latitude", lat),
        longitude=result.get("longitude", lon),
        source=result.get("source", "live")
    )


# ==================== AUTOCOMPLETE ENDPOINT (NEW - LEVEL 1) ====================

@router.get(
    "/autocomplete",
    summary="Autocomplete location search",
    description="""
    Fast autocomplete/typeahead search for locations.
    
    Perfect for:
    - Search-as-you-type interfaces
    - Mobile app location pickers
    - Quick city selection
    
    Returns minimal data for fast response times.
    
    **Parameters:**
    - `q`: Partial search query (min 2 characters)
    - `limit`: Maximum results (1-10, default 5)
    - `types`: Filter by location types (city, country, region)
    
    **Example:**
    ```
    curl "https://api.example.com/geocode/autocomplete?q=New Yo"
    ```
    """
)
async def autocomplete_locations(
    request: Request,
    q: str = Query(..., min_length=2, max_length=100, description="Partial search query"),
    limit: int = Query(5, ge=1, le=10, description="Maximum results"),
    types: Optional[str] = Query(None, description="Filter types: city,country,region")
):
    """Autocomplete search for locations with fast response."""
    metrics = get_metrics()
    metrics.api_requests_total.labels(endpoint="/geocode/autocomplete", method="GET").inc()
    
    # Cache autocomplete results aggressively (1 hour)
    cache_key = f"autocomplete:{q.lower()}:{limit}:{types}"
    cache = get_cache()
    
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.info(f"Cache hit for autocomplete: {q}")
        metrics.cache_hits_total.labels(cache_type="autocomplete").inc()
        return JSONResponse(content=cached_data)
    
    metrics.cache_misses_total.labels(cache_type="autocomplete").inc()
    
    # Perform search
    geocoding = get_geocoding_service()
    result = geocoding.search(q, limit, None)
    
    if result.get("source") == "error":
        raise HTTPException(
            status_code=503,
            detail="Autocomplete service temporarily unavailable"
        )
    
    # Format minimal response for autocomplete
    suggestions = []
    for loc in result.get("results", []):
        # Apply type filter if specified
        if types:
            type_list = [t.strip().lower() for t in types.split(",")]
            loc_type = loc.get("feature_type", "city").lower()
            if loc_type not in type_list:
                continue
        
        suggestion = {
            "id": loc.get("id"),
            "name": loc.get("name"),
            "country": loc.get("country"),
            "country_code": loc.get("country_code"),
            "latitude": loc.get("latitude"),
            "longitude": loc.get("longitude"),
            "admin1": loc.get("admin1"),  # State/Province
            "display_name": f"{loc.get('name')}, {loc.get('admin1', '')} {loc.get('country', '')}".strip().replace("  ", " ")
        }
        suggestions.append(suggestion)
    
    response_data = {
        "query": q,
        "suggestions": suggestions[:limit],
        "count": len(suggestions[:limit])
    }
    
    # Cache for 1 hour
    cache.set(cache_key, response_data, ttl=3600)
    
    return JSONResponse(content=response_data)


# ==================== POPULAR LOCATIONS ENDPOINT (NEW - LEVEL 1) ====================

@router.get(
    "/popular",
    summary="Get popular locations",
    description="""
    Get list of popular/frequently searched locations.
    
    Useful for:
    - Default location suggestions
    - Popular city lists
    - Quick access to major cities
    
    Pre-cached for instant response.
    """
)
async def get_popular_locations(
    request: Request,
    limit: int = Query(20, ge=1, le=100, description="Maximum results")
):
    """Get popular pre-cached locations."""
    metrics = get_metrics()
    metrics.api_requests_total.labels(endpoint="/geocode/popular", method="GET").inc()
    
    # Get popular locations from config
    popular = settings.parse_popular_locations()
    
    # Format response
    locations = []
    for loc in popular[:limit]:
        locations.append({
            "name": loc["name"],
            "latitude": loc["lat"],
            "longitude": loc["lon"],
            "display_name": loc["name"]
        })
    
    return JSONResponse(content={
        "locations": locations,
        "count": len(locations)
    })


# ==================== NEARBY CITIES ENDPOINT (NEW - LEVEL 1) ====================

@router.get(
    "/nearby",
    summary="Find nearby cities",
    description="""
    Find cities near a given location.
    
    Useful for:
    - "Weather near me" features
    - Alternative location suggestions
    - Regional weather overview
    
    **Parameters:**
    - `lat`: Latitude
    - `lon`: Longitude
    - `radius_km`: Search radius in kilometers (default 50, max 200)
    - `limit`: Maximum results
    """
)
async def find_nearby_cities(
    request: Request,
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    radius_km: int = Query(50, ge=1, le=200, description="Search radius in km"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results")
):
    """Find cities near given coordinates."""
    metrics = get_metrics()
    metrics.api_requests_total.labels(endpoint="/geocode/nearby", method="GET").inc()
    
    cache_key = f"nearby:{lat}:{lon}:{radius_km}:{limit}"
    cache = get_cache()
    
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.info(f"Cache hit for nearby cities: {lat},{lon}")
        metrics.cache_hits_total.labels(cache_type="nearby").inc()
        return JSONResponse(content=cached_data)
    
    metrics.cache_misses_total.labels(cache_type="nearby").inc()
    
    # Use geocoding service to search in area
    # This is a simplified implementation - in production, you'd use a spatial database
    geocoding = get_geocoding_service()
    
    # Search with empty query but coordinates (not all APIs support this)
    # For now, we'll return popular locations as a fallback
    popular = settings.parse_popular_locations()
    
    # Calculate distances and filter
    import math
    
    def haversine_distance(lat1, lon1, lat2, lon2):
        """Calculate distance between two points in km."""
        R = 6371  # Earth radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    nearby = []
    for loc in popular:
        distance = haversine_distance(lat, lon, loc["lat"], loc["lon"])
        if distance <= radius_km and distance > 0:  # Exclude exact match
            nearby.append({
                "name": loc["name"],
                "latitude": loc["lat"],
                "longitude": loc["lon"],
                "distance_km": round(distance, 1),
                "display_name": loc["name"]
            })
    
    # Sort by distance
    nearby.sort(key=lambda x: x["distance_km"])
    nearby = nearby[:limit]
    
    response_data = {
        "center": {"latitude": lat, "longitude": lon},
        "radius_km": radius_km,
        "cities": nearby,
        "count": len(nearby)
    }
    
    # Cache for 24 hours (nearby cities don't change)
    cache.set(cache_key, response_data, ttl=86400)
    
    return JSONResponse(content=response_data)
