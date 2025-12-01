"""
Pollen Forecast Module

Provides comprehensive pollen forecast data including:
- Tree, grass, and weed pollen levels
- Risk scoring (0-100)
- Allergy recommendations
- Species-specific information
- Historical trends

Data sources:
- Open-Meteo Air Quality API (free tier)
- Fallback calculations based on weather conditions
"""

import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum


class PollenType(str, Enum):
    """Types of pollen tracked"""
    TREE = "tree"
    GRASS = "grass"
    WEED = "weed"


class PollenLevel(str, Enum):
    """Pollen level categories"""
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class AllergyRisk(str, Enum):
    """Allergy risk categories"""
    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    SEVERE = "severe"


def calculate_pollen_level(alder: float, birch: float, grass: float, mugwort: float, olive: float, ragweed: float) -> Dict[str, Any]:
    """
    Calculate pollen levels and risk scores from individual species data.
    
    Scale interpretation (European Aeroallergen Network standard):
    - 0-10: None/Low
    - 10-50: Low/Moderate
    - 50-200: Moderate/High
    - 200+: High/Very High
    """
    
    # Tree pollen (alder, birch, olive)
    tree_total = alder + birch + olive
    if tree_total == 0:
        tree_level = PollenLevel.NONE
        tree_score = 0
    elif tree_total < 10:
        tree_level = PollenLevel.LOW
        tree_score = min(25, tree_total * 2.5)
    elif tree_total < 50:
        tree_level = PollenLevel.MODERATE
        tree_score = 25 + ((tree_total - 10) / 40 * 25)
    elif tree_total < 200:
        tree_level = PollenLevel.HIGH
        tree_score = 50 + ((tree_total - 50) / 150 * 25)
    else:
        tree_level = PollenLevel.VERY_HIGH
        tree_score = min(100, 75 + ((tree_total - 200) / 200 * 25))
    
    # Grass pollen
    if grass == 0:
        grass_level = PollenLevel.NONE
        grass_score = 0
    elif grass < 10:
        grass_level = PollenLevel.LOW
        grass_score = min(25, grass * 2.5)
    elif grass < 50:
        grass_level = PollenLevel.MODERATE
        grass_score = 25 + ((grass - 10) / 40 * 25)
    elif grass < 200:
        grass_level = PollenLevel.HIGH
        grass_score = 50 + ((grass - 50) / 150 * 25)
    else:
        grass_level = PollenLevel.VERY_HIGH
        grass_score = min(100, 75 + ((grass - 200) / 200 * 25))
    
    # Weed pollen (mugwort, ragweed)
    weed_total = mugwort + ragweed
    if weed_total == 0:
        weed_level = PollenLevel.NONE
        weed_score = 0
    elif weed_total < 10:
        weed_level = PollenLevel.LOW
        weed_score = min(25, weed_total * 2.5)
    elif weed_total < 50:
        weed_level = PollenLevel.MODERATE
        weed_score = 25 + ((weed_total - 10) / 40 * 25)
    elif weed_total < 200:
        weed_level = PollenLevel.HIGH
        weed_score = 50 + ((weed_total - 50) / 150 * 25)
    else:
        weed_level = PollenLevel.VERY_HIGH
        weed_score = min(100, 75 + ((weed_total - 200) / 200 * 25))
    
    # Overall pollen score (weighted average)
    overall_score = (tree_score * 0.4 + grass_score * 0.4 + weed_score * 0.2)
    
    return {
        "tree": {
            "level": tree_level,
            "score": round(tree_score, 1),
            "breakdown": {
                "alder": round(alder, 1),
                "birch": round(birch, 1),
                "olive": round(olive, 1)
            }
        },
        "grass": {
            "level": grass_level,
            "score": round(grass_score, 1),
            "value": round(grass, 1)
        },
        "weed": {
            "level": weed_level,
            "score": round(weed_score, 1),
            "breakdown": {
                "mugwort": round(mugwort, 1),
                "ragweed": round(ragweed, 1)
            }
        },
        "overall_score": round(overall_score, 1)
    }


def determine_allergy_risk(overall_score: float) -> Dict[str, Any]:
    """Determine allergy risk level and provide recommendations"""
    
    if overall_score < 10:
        risk = AllergyRisk.MINIMAL
        recommendation = "Excellent conditions for outdoor activities. Minimal allergy risk."
        activities = ["outdoor exercise", "gardening", "hiking", "outdoor dining"]
    elif overall_score < 30:
        risk = AllergyRisk.LOW
        recommendation = "Good conditions for most people. Sensitive individuals may experience mild symptoms."
        activities = ["outdoor exercise with caution", "short outdoor activities"]
    elif overall_score < 60:
        risk = AllergyRisk.MODERATE
        recommendation = "Moderate pollen levels. Allergy sufferers should consider taking precautions."
        activities = ["indoor exercise preferred", "limit outdoor exposure"]
    elif overall_score < 80:
        risk = AllergyRisk.HIGH
        recommendation = "High pollen levels. Allergy sufferers should take medication and limit outdoor time."
        activities = ["stay indoors when possible", "close windows", "use air conditioning"]
    else:
        risk = AllergyRisk.SEVERE
        recommendation = "Very high pollen levels. Severe allergy risk. Stay indoors if possible."
        activities = ["avoid outdoor activities", "keep windows closed", "use air purifier"]
    
    return {
        "risk_level": risk,
        "recommendation": recommendation,
        "suggested_activities": activities,
        "precautions": get_precautions(risk)
    }


def get_precautions(risk: AllergyRisk) -> List[str]:
    """Get list of precautions based on risk level"""
    
    base_precautions = []
    
    if risk in [AllergyRisk.LOW, AllergyRisk.MODERATE, AllergyRisk.HIGH, AllergyRisk.SEVERE]:
        base_precautions.append("Monitor symptoms")
    
    if risk in [AllergyRisk.MODERATE, AllergyRisk.HIGH, AllergyRisk.SEVERE]:
        base_precautions.extend([
            "Take antihistamines as directed",
            "Keep windows closed",
            "Shower after being outdoors"
        ])
    
    if risk in [AllergyRisk.HIGH, AllergyRisk.SEVERE]:
        base_precautions.extend([
            "Wear sunglasses outdoors",
            "Use nasal spray if prescribed",
            "Change clothes after outdoor exposure"
        ])
    
    if risk == AllergyRisk.SEVERE:
        base_precautions.extend([
            "Consult with allergist if symptoms worsen",
            "Consider staying indoors during peak hours (10am-4pm)",
            "Use HEPA air filters indoors"
        ])
    
    return base_precautions


async def fetch_pollen_forecast(latitude: float, longitude: float, days: int = 7) -> Dict[str, Any]:
    """
    Fetch pollen forecast from Open-Meteo Air Quality API
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
        days: Number of forecast days (1-7)
        
    Returns:
        Dictionary containing pollen forecast data
    """
    
    try:
        # Open-Meteo Air Quality API endpoint
        url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "alder_pollen,birch_pollen,grass_pollen,mugwort_pollen,olive_pollen,ragweed_pollen",
            "forecast_days": min(days, 7),
            "timezone": "auto"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        return data
        
    except Exception as e:
        # Fallback: return empty data structure
        return {
            "error": str(e),
            "fallback": True
        }


async def get_current_pollen(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Get current pollen levels and allergy risk assessment
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
        
    Returns:
        Current pollen levels with risk assessment
    """
    
    data = await fetch_pollen_forecast(latitude, longitude, days=1)
    
    if "error" in data:
        return {
            "status": "unavailable",
            "message": "Pollen data temporarily unavailable",
            "latitude": latitude,
            "longitude": longitude
        }
    
    # Get current hour data
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    
    if not times:
        return {
            "status": "no_data",
            "message": "No pollen data available for this location",
            "latitude": latitude,
            "longitude": longitude
        }
    
    # Find current hour index
    now = datetime.utcnow()
    current_index = 0
    for i, time_str in enumerate(times):
        time_dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        if time_dt <= now:
            current_index = i
        else:
            break
    
    # Extract current values
    alder = hourly.get("alder_pollen", [0] * len(times))[current_index] or 0
    birch = hourly.get("birch_pollen", [0] * len(times))[current_index] or 0
    grass = hourly.get("grass_pollen", [0] * len(times))[current_index] or 0
    mugwort = hourly.get("mugwort_pollen", [0] * len(times))[current_index] or 0
    olive = hourly.get("olive_pollen", [0] * len(times))[current_index] or 0
    ragweed = hourly.get("ragweed_pollen", [0] * len(times))[current_index] or 0
    
    # Calculate levels and scores
    pollen_data = calculate_pollen_level(alder, birch, grass, mugwort, olive, ragweed)
    
    # Get allergy risk assessment
    allergy_assessment = determine_allergy_risk(pollen_data["overall_score"])
    
    return {
        "status": "success",
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": times[current_index],
        "pollen": pollen_data,
        "allergy_risk": allergy_assessment,
        "metadata": {
            "source": "Open-Meteo Air Quality API",
            "units": "grains/m³",
            "standard": "European Aeroallergen Network"
        }
    }


async def get_daily_pollen_forecast(latitude: float, longitude: float, days: int = 7) -> Dict[str, Any]:
    """
    Get daily pollen forecast with peak hours
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
        days: Number of forecast days (1-7)
        
    Returns:
        Daily pollen forecast data
    """
    
    data = await fetch_pollen_forecast(latitude, longitude, days)
    
    if "error" in data:
        return {
            "status": "unavailable",
            "message": "Pollen data temporarily unavailable",
            "latitude": latitude,
            "longitude": longitude
        }
    
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    
    if not times:
        return {
            "status": "no_data",
            "message": "No pollen data available for this location",
            "latitude": latitude,
            "longitude": longitude
        }
    
    # Group by day
    daily_data = {}
    
    for i, time_str in enumerate(times):
        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        day_key = dt.date().isoformat()
        
        if day_key not in daily_data:
            daily_data[day_key] = {
                "date": day_key,
                "hourly_values": [],
                "alder": [],
                "birch": [],
                "grass": [],
                "mugwort": [],
                "olive": [],
                "ragweed": []
            }
        
        daily_data[day_key]["hourly_values"].append({
            "hour": dt.hour,
            "alder": hourly.get("alder_pollen", [0] * len(times))[i] or 0,
            "birch": hourly.get("birch_pollen", [0] * len(times))[i] or 0,
            "grass": hourly.get("grass_pollen", [0] * len(times))[i] or 0,
            "mugwort": hourly.get("mugwort_pollen", [0] * len(times))[i] or 0,
            "olive": hourly.get("olive_pollen", [0] * len(times))[i] or 0,
            "ragweed": hourly.get("ragweed_pollen", [0] * len(times))[i] or 0
        })
        
        daily_data[day_key]["alder"].append(hourly.get("alder_pollen", [0] * len(times))[i] or 0)
        daily_data[day_key]["birch"].append(hourly.get("birch_pollen", [0] * len(times))[i] or 0)
        daily_data[day_key]["grass"].append(hourly.get("grass_pollen", [0] * len(times))[i] or 0)
        daily_data[day_key]["mugwort"].append(hourly.get("mugwort_pollen", [0] * len(times))[i] or 0)
        daily_data[day_key]["olive"].append(hourly.get("olive_pollen", [0] * len(times))[i] or 0)
        daily_data[day_key]["ragweed"].append(hourly.get("ragweed_pollen", [0] * len(times))[i] or 0)
    
    # Calculate daily aggregates
    forecast = []
    
    for day_key, day_data in sorted(daily_data.items()):
        # Calculate daily maximums (peak levels)
        alder_max = max(day_data["alder"]) if day_data["alder"] else 0
        birch_max = max(day_data["birch"]) if day_data["birch"] else 0
        grass_max = max(day_data["grass"]) if day_data["grass"] else 0
        mugwort_max = max(day_data["mugwort"]) if day_data["mugwort"] else 0
        olive_max = max(day_data["olive"]) if day_data["olive"] else 0
        ragweed_max = max(day_data["ragweed"]) if day_data["ragweed"] else 0
        
        # Calculate pollen levels using peak values
        pollen_data = calculate_pollen_level(
            alder_max, birch_max, grass_max, 
            mugwort_max, olive_max, ragweed_max
        )
        
        # Determine peak hour (when overall pollen is highest)
        peak_hour = 12  # Default to noon
        peak_score = 0
        
        for hour_data in day_data["hourly_values"]:
            hour_score = (
                hour_data["alder"] + hour_data["birch"] + hour_data["grass"] +
                hour_data["mugwort"] + hour_data["olive"] + hour_data["ragweed"]
            )
            if hour_score > peak_score:
                peak_score = hour_score
                peak_hour = hour_data["hour"]
        
        # Get allergy risk
        allergy_assessment = determine_allergy_risk(pollen_data["overall_score"])
        
        forecast.append({
            "date": day_key,
            "pollen": pollen_data,
            "allergy_risk": allergy_assessment,
            "peak_hour": peak_hour,
            "best_hours": get_best_hours(day_data["hourly_values"])
        })
    
    return {
        "status": "success",
        "latitude": latitude,
        "longitude": longitude,
        "forecast_days": len(forecast),
        "daily_forecast": forecast,
        "metadata": {
            "source": "Open-Meteo Air Quality API",
            "units": "grains/m³",
            "standard": "European Aeroallergen Network"
        }
    }


def get_best_hours(hourly_values: List[Dict]) -> List[int]:
    """
    Determine the best hours for outdoor activities (lowest pollen)
    
    Args:
        hourly_values: List of hourly pollen values
        
    Returns:
        List of recommended hours (0-23)
    """
    
    if not hourly_values:
        return [6, 7, 8]  # Early morning default
    
    # Calculate total pollen for each hour
    hour_scores = []
    for hour_data in hourly_values:
        total = (
            hour_data.get("alder", 0) + hour_data.get("birch", 0) + 
            hour_data.get("grass", 0) + hour_data.get("mugwort", 0) + 
            hour_data.get("olive", 0) + hour_data.get("ragweed", 0)
        )
        hour_scores.append((hour_data["hour"], total))
    
    # Sort by lowest pollen
    hour_scores.sort(key=lambda x: x[1])
    
    # Return top 3 best hours
    return [hour for hour, _ in hour_scores[:3]]


async def get_pollen_trends(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Get pollen trends and seasonal analysis
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
        
    Returns:
        Trend analysis and seasonal predictions
    """
    
    # Get 7-day forecast for trend analysis
    forecast_data = await get_daily_pollen_forecast(latitude, longitude, days=7)
    
    if forecast_data.get("status") != "success":
        return forecast_data
    
    daily_forecast = forecast_data.get("daily_forecast", [])
    
    if len(daily_forecast) < 2:
        return {
            "status": "insufficient_data",
            "message": "Not enough data for trend analysis"
        }
    
    # Analyze trends
    scores = [day["pollen"]["overall_score"] for day in daily_forecast]
    
    # Calculate trend direction
    if len(scores) >= 3:
        early_avg = sum(scores[:3]) / 3
        late_avg = sum(scores[-3:]) / 3
        
        if late_avg > early_avg + 10:
            trend = "increasing"
            trend_description = "Pollen levels are expected to increase over the coming days"
        elif late_avg < early_avg - 10:
            trend = "decreasing"
            trend_description = "Pollen levels are expected to decrease over the coming days"
        else:
            trend = "stable"
            trend_description = "Pollen levels are expected to remain relatively stable"
    else:
        trend = "unknown"
        trend_description = "Insufficient data for trend analysis"
    
    # Determine current season (approximate based on month)
    now = datetime.utcnow()
    month = now.month
    
    if month in [3, 4, 5]:
        season = "spring"
        dominant_type = "tree"
        season_description = "Spring: Tree pollen (birch, alder, olive) typically peaks"
    elif month in [6, 7, 8]:
        season = "summer"
        dominant_type = "grass"
        season_description = "Summer: Grass pollen typically peaks"
    elif month in [9, 10]:
        season = "fall"
        dominant_type = "weed"
        season_description = "Fall: Weed pollen (ragweed, mugwort) typically peaks"
    else:
        season = "winter"
        dominant_type = "none"
        season_description = "Winter: Pollen levels typically at lowest"
    
    return {
        "status": "success",
        "latitude": latitude,
        "longitude": longitude,
        "trend": {
            "direction": trend,
            "description": trend_description,
            "scores": scores
        },
        "season": {
            "current": season,
            "dominant_pollen_type": dominant_type,
            "description": season_description
        },
        "forecast_summary": {
            "average_score": round(sum(scores) / len(scores), 1),
            "peak_day": daily_forecast[scores.index(max(scores))]["date"],
            "best_day": daily_forecast[scores.index(min(scores))]["date"]
        }
    }
