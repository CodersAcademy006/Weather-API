"""
Geocoding Routes

Provides geocoding and reverse geocoding endpoints.
"""

from fastapi import APIRouter, HTTPException, Query, Request

from config import settings
from logging_config import get_logger
from metrics import get_metrics
from modules.geocode import get_geocoding_service
from schemas.geocode import (
    GeocodeSearchResponse,
    ReverseGeocodeResponse,
    GeoLocation
)

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
