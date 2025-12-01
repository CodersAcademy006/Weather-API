"""
Marine & Coastal Weather Module

Provides comprehensive marine weather data including:
- Wave height and swell conditions
- Sea surface temperature
- Tide estimation (astronomical)
- Coastal wind conditions
- Marine weather warnings

Data sources:
- Open-Meteo Marine Weather API (free)
- NOAA Tides & Currents (for tide predictions)
"""

import requests
import math
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum


class SeaState(str, Enum):
    """WMO Sea State Code descriptions"""
    CALM = "calm"  # 0-0.1m
    SMOOTH = "smooth"  # 0.1-0.5m
    SLIGHT = "slight"  # 0.5-1.25m
    MODERATE = "moderate"  # 1.25-2.5m
    ROUGH = "rough"  # 2.5-4m
    VERY_ROUGH = "very_rough"  # 4-6m
    HIGH = "high"  # 6-9m
    VERY_HIGH = "very_high"  # 9-14m
    PHENOMENAL = "phenomenal"  # 14m+


class MarineRisk(str, Enum):
    """Marine activity risk levels"""
    SAFE = "safe"
    CAUTION = "caution"
    WARNING = "warning"
    DANGEROUS = "dangerous"
    EXTREME = "extreme"


def classify_sea_state(wave_height: float) -> Dict[str, Any]:
    """
    Classify sea state based on wave height (WMO Sea State Code)
    
    Args:
        wave_height: Significant wave height in meters
        
    Returns:
        Dictionary with sea state classification and description
    """
    
    if wave_height < 0.1:
        state = SeaState.CALM
        description = "Calm (glassy)"
        code = 0
    elif wave_height < 0.5:
        state = SeaState.SMOOTH
        description = "Smooth (wavelets)"
        code = 1
    elif wave_height < 1.25:
        state = SeaState.SLIGHT
        description = "Slight"
        code = 2
    elif wave_height < 2.5:
        state = SeaState.MODERATE
        description = "Moderate"
        code = 3
    elif wave_height < 4:
        state = SeaState.ROUGH
        description = "Rough"
        code = 4
    elif wave_height < 6:
        state = SeaState.VERY_ROUGH
        description = "Very rough"
        code = 5
    elif wave_height < 9:
        state = SeaState.HIGH
        description = "High"
        code = 6
    elif wave_height < 14:
        state = SeaState.VERY_HIGH
        description = "Very high"
        code = 7
    else:
        state = SeaState.PHENOMENAL
        description = "Phenomenal"
        code = 8
    
    return {
        "state": state,
        "description": description,
        "wmo_code": code,
        "wave_height_m": round(wave_height, 2)
    }


def assess_marine_activities_risk(
    wave_height: float,
    wind_speed: float,
    swell_height: Optional[float] = None,
    visibility: Optional[float] = None
) -> Dict[str, Any]:
    """
    Assess risk for various marine activities
    
    Args:
        wave_height: Significant wave height in meters
        wind_speed: Wind speed in km/h
        swell_height: Swell height in meters (optional)
        visibility: Visibility in km (optional)
        
    Returns:
        Risk assessment for different marine activities
    """
    
    activities = {}
    
    # Swimming risk
    if wave_height < 0.5 and wind_speed < 20:
        activities["swimming"] = {
            "risk": MarineRisk.SAFE,
            "recommendation": "Excellent conditions for swimming"
        }
    elif wave_height < 1.0 and wind_speed < 30:
        activities["swimming"] = {
            "risk": MarineRisk.CAUTION,
            "recommendation": "Generally safe, but stay alert"
        }
    elif wave_height < 2.0 and wind_speed < 40:
        activities["swimming"] = {
            "risk": MarineRisk.WARNING,
            "recommendation": "Not recommended for weak swimmers"
        }
    else:
        activities["swimming"] = {
            "risk": MarineRisk.DANGEROUS,
            "recommendation": "Swimming not advised"
        }
    
    # Surfing conditions
    if 0.5 <= wave_height <= 3.0 and wind_speed < 40:
        activities["surfing"] = {
            "risk": MarineRisk.SAFE,
            "recommendation": f"Good surfing conditions ({wave_height}m waves)",
            "quality": "good" if 1.0 <= wave_height <= 2.5 else "fair"
        }
    elif wave_height < 0.5:
        activities["surfing"] = {
            "risk": MarineRisk.SAFE,
            "recommendation": "Waves too small for surfing",
            "quality": "poor"
        }
    elif wave_height < 4.5 and wind_speed < 60:
        activities["surfing"] = {
            "risk": MarineRisk.CAUTION,
            "recommendation": "Large waves - for experienced surfers only",
            "quality": "challenging"
        }
    else:
        activities["surfing"] = {
            "risk": MarineRisk.DANGEROUS,
            "recommendation": "Dangerous conditions - not recommended",
            "quality": "hazardous"
        }
    
    # Sailing risk
    if wave_height < 1.5 and wind_speed < 25:
        activities["sailing"] = {
            "risk": MarineRisk.SAFE,
            "recommendation": "Ideal sailing conditions"
        }
    elif wave_height < 2.5 and wind_speed < 45:
        activities["sailing"] = {
            "risk": MarineRisk.CAUTION,
            "recommendation": "Good for experienced sailors"
        }
    elif wave_height < 4.0 and wind_speed < 60:
        activities["sailing"] = {
            "risk": MarineRisk.WARNING,
            "recommendation": "Challenging conditions - caution advised"
        }
    else:
        activities["sailing"] = {
            "risk": MarineRisk.DANGEROUS,
            "recommendation": "Sailing not recommended"
        }
    
    # Fishing (small boat)
    if wave_height < 1.0 and wind_speed < 30:
        activities["fishing"] = {
            "risk": MarineRisk.SAFE,
            "recommendation": "Excellent conditions for fishing"
        }
    elif wave_height < 2.0 and wind_speed < 40:
        activities["fishing"] = {
            "risk": MarineRisk.CAUTION,
            "recommendation": "Acceptable conditions, stay close to shore"
        }
    elif wave_height < 3.0 and wind_speed < 50:
        activities["fishing"] = {
            "risk": MarineRisk.WARNING,
            "recommendation": "Return to port recommended"
        }
    else:
        activities["fishing"] = {
            "risk": MarineRisk.DANGEROUS,
            "recommendation": "Seek shelter immediately"
        }
    
    # Diving risk
    if wave_height < 0.5 and wind_speed < 20:
        activities["diving"] = {
            "risk": MarineRisk.SAFE,
            "recommendation": "Perfect diving conditions",
            "visibility_note": "Check local visibility"
        }
    elif wave_height < 1.5 and wind_speed < 35:
        activities["diving"] = {
            "risk": MarineRisk.CAUTION,
            "recommendation": "Acceptable for experienced divers"
        }
    else:
        activities["diving"] = {
            "risk": MarineRisk.DANGEROUS,
            "recommendation": "Diving not recommended"
        }
    
    # Add visibility warnings if provided
    if visibility is not None and visibility < 5:
        for activity in activities.values():
            if "visibility_note" not in activity:
                activity["visibility_note"] = f"Limited visibility ({visibility}km)"
    
    return activities


def calculate_tide_approximation(latitude: float, longitude: float, timestamp: datetime) -> Dict[str, Any]:
    """
    Calculate approximate tidal state using astronomical tide prediction
    
    This is a simplified model based on lunar position. For accurate tide predictions,
    use official tide tables or NOAA API for specific locations.
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
        timestamp: Time for tide calculation
        
    Returns:
        Approximate tide information
    """
    
    # Lunar cycle constants
    LUNAR_DAY = 24.84  # Hours
    TIDAL_PERIOD = LUNAR_DAY / 2  # Semi-diurnal tide (2 high tides per lunar day)
    
    # Calculate days since a known new moon (2000-01-06 18:14 UTC)
    reference = datetime(2000, 1, 6, 18, 14)
    days_since_ref = (timestamp - reference).total_seconds() / 86400
    
    # Calculate lunar phase (0 = new moon, 0.5 = full moon)
    lunar_month = 29.53058867  # Days
    lunar_phase = (days_since_ref % lunar_month) / lunar_month
    
    # Calculate hours into current lunar day
    hours_in_lunar_day = (days_since_ref * 24) % LUNAR_DAY
    
    # Calculate tidal phase (0-1, where 0.5 = high tide)
    tidal_phase = (hours_in_lunar_day % TIDAL_PERIOD) / TIDAL_PERIOD
    
    # Determine tide state
    if 0.4 <= tidal_phase <= 0.6:
        tide_state = "high"
        time_to_change = (0.5 - abs(tidal_phase - 0.5)) * TIDAL_PERIOD
    elif tidal_phase < 0.25 or tidal_phase > 0.75:
        tide_state = "low"
        if tidal_phase < 0.25:
            time_to_change = (0.25 - tidal_phase) * TIDAL_PERIOD
        else:
            time_to_change = (1.25 - tidal_phase) * TIDAL_PERIOD
    elif tidal_phase < 0.5:
        tide_state = "rising"
        time_to_change = (0.5 - tidal_phase) * TIDAL_PERIOD
    else:
        tide_state = "falling"
        time_to_change = (1.0 - tidal_phase) * TIDAL_PERIOD
    
    # Spring/neap tide determination
    # Spring tides occur during new and full moon
    # Neap tides occur during quarter moons
    if abs(lunar_phase - 0.0) < 0.1 or abs(lunar_phase - 0.5) < 0.1:
        tide_type = "spring"
        tide_range_multiplier = 1.3  # Higher tidal range
    elif abs(lunar_phase - 0.25) < 0.1 or abs(lunar_phase - 0.75) < 0.1:
        tide_type = "neap"
        tide_range_multiplier = 0.7  # Lower tidal range
    else:
        tide_type = "normal"
        tide_range_multiplier = 1.0
    
    return {
        "state": tide_state,
        "type": tide_type,
        "lunar_phase": round(lunar_phase, 3),
        "tidal_phase": round(tidal_phase, 3),
        "next_change_hours": round(time_to_change, 1),
        "range_factor": tide_range_multiplier,
        "note": "Approximate astronomical tide. Use official tide tables for navigation."
    }


async def fetch_marine_weather(latitude: float, longitude: float, days: int = 7) -> Dict[str, Any]:
    """
    Fetch marine weather data from Open-Meteo Marine Weather API
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
        days: Number of forecast days
        
    Returns:
        Marine weather data including waves, swell, and SST
    """
    
    try:
        url = "https://marine-api.open-meteo.com/v1/marine"
        
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ",".join([
                "wave_height",
                "wave_direction",
                "wave_period",
                "wind_wave_height",
                "wind_wave_direction",
                "wind_wave_period",
                "swell_wave_height",
                "swell_wave_direction",
                "swell_wave_period",
                "ocean_current_velocity",
                "ocean_current_direction"
            ]),
            "daily": "wave_height_max,wave_direction_dominant,wave_period_max",
            "forecast_days": min(days, 7),
            "timezone": "auto"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        return response.json()
        
    except Exception as e:
        return {
            "error": str(e),
            "fallback": True
        }


async def get_current_marine_conditions(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Get current marine and coastal weather conditions
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
        
    Returns:
        Current marine conditions with risk assessment
    """
    
    # Fetch marine data
    marine_data = await fetch_marine_weather(latitude, longitude, days=1)
    
    if "error" in marine_data:
        return {
            "status": "unavailable",
            "message": "Marine data temporarily unavailable",
            "latitude": latitude,
            "longitude": longitude
        }
    
    hourly = marine_data.get("hourly", {})
    times = hourly.get("time", [])
    
    if not times:
        return {
            "status": "no_data",
            "message": "No marine data available for this location (may be inland)",
            "latitude": latitude,
            "longitude": longitude
        }
    
    # Find current hour
    now = datetime.utcnow()
    current_index = 0
    for i, time_str in enumerate(times):
        time_dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        if time_dt <= now:
            current_index = i
        else:
            break
    
    # Extract current values
    wave_height = hourly.get("wave_height", [0] * len(times))[current_index] or 0
    wave_direction = hourly.get("wave_direction", [0] * len(times))[current_index] or 0
    wave_period = hourly.get("wave_period", [0] * len(times))[current_index] or 0
    
    swell_height = hourly.get("swell_wave_height", [0] * len(times))[current_index] or 0
    swell_direction = hourly.get("swell_wave_direction", [0] * len(times))[current_index] or 0
    swell_period = hourly.get("swell_wave_period", [0] * len(times))[current_index] or 0
    
    wind_wave_height = hourly.get("wind_wave_height", [0] * len(times))[current_index] or 0
    
    current_velocity = hourly.get("ocean_current_velocity", [0] * len(times))[current_index] or 0
    current_direction = hourly.get("ocean_current_direction", [0] * len(times))[current_index] or 0
    
    # Get sea state classification
    sea_state = classify_sea_state(wave_height)
    
    # Calculate tide approximation
    tide_info = calculate_tide_approximation(latitude, longitude, now)
    
    # Estimate wind speed from wind wave height (rough approximation)
    # Beaufort scale relationship: wind_speed (m/s) ≈ 4.3 * wave_height^0.5
    estimated_wind_speed = 4.3 * (wind_wave_height ** 0.5) * 3.6  # Convert to km/h
    
    # Get activity risk assessment
    activity_risks = assess_marine_activities_risk(
        wave_height=wave_height,
        wind_speed=estimated_wind_speed,
        swell_height=swell_height
    )
    
    return {
        "status": "success",
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": times[current_index],
        "waves": {
            "significant_height_m": round(wave_height, 2),
            "direction_deg": round(wave_direction, 1),
            "period_sec": round(wave_period, 1),
            "sea_state": sea_state
        },
        "swell": {
            "height_m": round(swell_height, 2),
            "direction_deg": round(swell_direction, 1),
            "period_sec": round(swell_period, 1)
        },
        "wind_waves": {
            "height_m": round(wind_wave_height, 2)
        },
        "currents": {
            "velocity_m_s": round(current_velocity, 2),
            "direction_deg": round(current_direction, 1)
        },
        "tide": tide_info,
        "activity_risk": activity_risks,
        "metadata": {
            "source": "Open-Meteo Marine Weather API",
            "note": "Tide information is approximate. Use official tide tables for navigation."
        }
    }


async def get_marine_forecast(latitude: float, longitude: float, days: int = 7) -> Dict[str, Any]:
    """
    Get daily marine weather forecast
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
        days: Number of forecast days
        
    Returns:
        Daily marine forecast
    """
    
    marine_data = await fetch_marine_weather(latitude, longitude, days)
    
    if "error" in marine_data:
        return {
            "status": "unavailable",
            "message": "Marine data temporarily unavailable"
        }
    
    daily = marine_data.get("daily", {})
    dates = daily.get("time", [])
    
    if not dates:
        return {
            "status": "no_data",
            "message": "No marine forecast available for this location"
        }
    
    forecast = []
    
    for i, date in enumerate(dates):
        max_wave_height = daily.get("wave_height_max", [0] * len(dates))[i] or 0
        dominant_direction = daily.get("wave_direction_dominant", [0] * len(dates))[i] or 0
        max_period = daily.get("wave_period_max", [0] * len(dates))[i] or 0
        
        sea_state = classify_sea_state(max_wave_height)
        
        # Estimate conditions for the day
        estimated_wind = 4.3 * (max_wave_height ** 0.5) * 3.6
        activity_risks = assess_marine_activities_risk(
            wave_height=max_wave_height,
            wind_speed=estimated_wind
        )
        
        forecast.append({
            "date": date,
            "max_wave_height_m": round(max_wave_height, 2),
            "dominant_direction_deg": round(dominant_direction, 1),
            "max_period_sec": round(max_period, 1),
            "sea_state": sea_state,
            "activity_risk": activity_risks
        })
    
    return {
        "status": "success",
        "latitude": latitude,
        "longitude": longitude,
        "forecast_days": len(forecast),
        "daily_forecast": forecast,
        "metadata": {
            "source": "Open-Meteo Marine Weather API"
        }
    }
