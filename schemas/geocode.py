"""
Geocoding Schemas

Provides Pydantic models for geocoding and reverse geocoding endpoints.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class GeoLocation(BaseModel):
    """Geographic location with metadata."""
    id: int = Field(..., description="Unique location ID")
    name: str = Field(..., description="Location name", example="New York")
    latitude: float = Field(..., description="Latitude", example=40.7128)
    longitude: float = Field(..., description="Longitude", example=-74.006)
    country: str = Field(..., description="Country name", example="United States")
    country_code: Optional[str] = Field(None, description="ISO country code", example="US")
    admin1: Optional[str] = Field(None, description="State/Province", example="New York")
    admin2: Optional[str] = Field(None, description="County/District", example="New York County")
    timezone: Optional[str] = Field(None, description="Timezone", example="America/New_York")
    population: Optional[int] = Field(None, description="Population", example=8336817)
    elevation: Optional[float] = Field(None, description="Elevation in meters", example=10)
    feature_code: Optional[str] = Field(None, description="GeoNames feature code", example="PPL")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 5128581,
                "name": "New York",
                "latitude": 40.7128,
                "longitude": -74.006,
                "country": "United States",
                "country_code": "US",
                "admin1": "New York",
                "timezone": "America/New_York",
                "population": 8336817
            }
        }


class GeocodeSearchRequest(BaseModel):
    """Request model for geocode search."""
    q: str = Field(..., min_length=1, max_length=200, description="Search query", example="New York")
    limit: int = Field(5, ge=1, le=20, description="Maximum results to return")
    lang: Optional[str] = Field(None, description="Language for results", example="en")


class GeocodeSearchResponse(BaseModel):
    """Response model for geocode search."""
    results: List[GeoLocation] = Field(..., description="List of matching locations")
    query: str = Field(..., description="Original search query")
    count: int = Field(..., description="Number of results returned")
    source: str = Field(..., description="Data source (cache/live)", example="cache")

    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "id": 5128581,
                        "name": "New York",
                        "latitude": 40.7128,
                        "longitude": -74.006,
                        "country": "United States",
                        "country_code": "US",
                        "timezone": "America/New_York"
                    }
                ],
                "query": "New York",
                "count": 1,
                "source": "live"
            }
        }


class ReverseGeocodeRequest(BaseModel):
    """Request model for reverse geocoding."""
    lat: float = Field(..., ge=-90, le=90, description="Latitude", example=40.7128)
    lon: float = Field(..., ge=-180, le=180, description="Longitude", example=-74.006)


class ReverseGeocodeResponse(BaseModel):
    """Response model for reverse geocoding."""
    location: Optional[GeoLocation] = Field(None, description="Nearest location")
    latitude: float = Field(..., description="Queried latitude")
    longitude: float = Field(..., description="Queried longitude")
    source: str = Field(..., description="Data source (cache/live)")

    class Config:
        json_schema_extra = {
            "example": {
                "location": {
                    "id": 5128581,
                    "name": "New York",
                    "latitude": 40.7128,
                    "longitude": -74.006,
                    "country": "United States"
                },
                "latitude": 40.7128,
                "longitude": -74.006,
                "source": "cache"
            }
        }
