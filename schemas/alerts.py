"""
Weather Alerts Schemas

Provides Pydantic models for weather alerts and warnings.
"""

from datetime import datetime
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    EXTREME = "extreme"
    SEVERE = "severe"
    MODERATE = "moderate"
    MINOR = "minor"
    UNKNOWN = "unknown"


class AlertUrgency(str, Enum):
    """Alert urgency levels."""
    IMMEDIATE = "immediate"
    EXPECTED = "expected"
    FUTURE = "future"
    PAST = "past"
    UNKNOWN = "unknown"


class AlertCertainty(str, Enum):
    """Alert certainty levels."""
    OBSERVED = "observed"
    LIKELY = "likely"
    POSSIBLE = "possible"
    UNLIKELY = "unlikely"
    UNKNOWN = "unknown"


class WeatherAlert(BaseModel):
    """Weather alert model."""
    id: str = Field(..., description="Unique alert ID")
    event: str = Field(..., description="Alert event type", example="Severe Thunderstorm Warning")
    headline: str = Field(..., description="Alert headline")
    description: str = Field(..., description="Detailed description")
    severity: AlertSeverity = Field(..., description="Alert severity level")
    urgency: Optional[AlertUrgency] = Field(None, description="Alert urgency")
    certainty: Optional[AlertCertainty] = Field(None, description="Alert certainty")
    start: str = Field(..., description="Alert start time (ISO 8601)")
    end: Optional[str] = Field(None, description="Alert end time (ISO 8601)")
    areas_affected: List[str] = Field(default_factory=list, description="Affected areas")
    sender: Optional[str] = Field(None, description="Alert sender/source")
    instruction: Optional[str] = Field(None, description="Safety instructions")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "alert-12345",
                "event": "Severe Thunderstorm Warning",
                "headline": "Severe Thunderstorm Warning issued for New York County",
                "description": "The National Weather Service has issued a severe thunderstorm warning...",
                "severity": "severe",
                "urgency": "immediate",
                "certainty": "observed",
                "start": "2024-01-15T14:00:00Z",
                "end": "2024-01-15T18:00:00Z",
                "areas_affected": ["New York County", "Kings County"],
                "sender": "NWS New York NY",
                "instruction": "Move to an interior room on the lowest floor of a building."
            }
        }


class AlertsResponse(BaseModel):
    """Response model for alerts endpoint."""
    latitude: float = Field(..., description="Queried latitude")
    longitude: float = Field(..., description="Queried longitude")
    location_name: Optional[str] = Field(None, description="Location name")
    alerts: List[WeatherAlert] = Field(default_factory=list, description="Active alerts")
    count: int = Field(..., description="Number of active alerts")
    last_updated: str = Field(..., description="When alerts were last fetched")
    source: str = Field(..., description="Data source (cache/live)")

    class Config:
        json_schema_extra = {
            "example": {
                "latitude": 40.7128,
                "longitude": -74.006,
                "location_name": "New York",
                "alerts": [],
                "count": 0,
                "last_updated": "2024-01-15T12:00:00Z",
                "source": "live"
            }
        }


class AlertsRefreshRequest(BaseModel):
    """Request to manually refresh alerts."""
    locations: Optional[List[str]] = Field(
        None, 
        description="Specific locations to refresh (lat,lon format). If empty, refreshes popular locations."
    )


class AlertsRefreshResponse(BaseModel):
    """Response for alerts refresh."""
    refreshed_locations: int = Field(..., description="Number of locations refreshed")
    alerts_found: int = Field(..., description="Total alerts found")
    timestamp: str = Field(..., description="Refresh timestamp")
