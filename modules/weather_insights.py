"""
Weather Insights Module - Calculated Weather Intelligence

Provides proprietary weather calculations and insights:
- Heat Index
- Wind Chill
- Wet Bulb Temperature
- Fire Risk Score
- UV Exposure Score
- Travel Disruption Risk
- Rain Probability Confidence

These are computed from raw weather data, not API-dependent.
"""

import math
from typing import Optional, Dict, Tuple
from datetime import datetime


# ==================== TEMPERATURE FEELS-LIKE CALCULATIONS ====================

def calculate_heat_index(temp_c: float, humidity: float) -> float:
    """
    Calculate heat index (feels-like temperature in hot conditions).
    
    Uses Rothfusz regression (NWS formula).
    Accurate for temperatures > 27°C (80°F) and humidity > 40%.
    
    Args:
        temp_c: Temperature in Celsius
        humidity: Relative humidity (0-100)
    
    Returns:
        Heat index in Celsius
    """
    # Convert to Fahrenheit for calculation
    temp_f = temp_c * 9/5 + 32
    
    # Simple formula for low temperatures
    if temp_f < 80:
        return temp_c
    
    # Rothfusz regression coefficients
    c1 = -42.379
    c2 = 2.04901523
    c3 = 10.14333127
    c4 = -0.22475541
    c5 = -0.00683783
    c6 = -0.05481717
    c7 = 0.00122874
    c8 = 0.00085282
    c9 = -0.00000199
    
    T = temp_f
    RH = humidity
    
    HI = (c1 + c2*T + c3*RH + c4*T*RH + c5*T*T + c6*RH*RH + 
          c7*T*T*RH + c8*T*RH*RH + c9*T*T*RH*RH)
    
    # Adjustments
    if RH < 13 and 80 <= T <= 112:
        adjustment = ((13 - RH) / 4) * math.sqrt((17 - abs(T - 95)) / 17)
        HI -= adjustment
    elif RH > 85 and 80 <= T <= 87:
        adjustment = ((RH - 85) / 10) * ((87 - T) / 5)
        HI += adjustment
    
    # Convert back to Celsius
    return (HI - 32) * 5/9


def calculate_wind_chill(temp_c: float, wind_speed_kmh: float) -> float:
    """
    Calculate wind chill (feels-like temperature in cold, windy conditions).
    
    Uses NWS/Environment Canada formula.
    Accurate for temperatures < 10°C and wind speeds > 4.8 km/h.
    
    Args:
        temp_c: Temperature in Celsius
        wind_speed_kmh: Wind speed in km/h
    
    Returns:
        Wind chill in Celsius
    """
    if temp_c > 10 or wind_speed_kmh < 4.8:
        return temp_c
    
    # Wind chill formula (metric)
    WC = (13.12 + 0.6215*temp_c - 11.37*math.pow(wind_speed_kmh, 0.16) + 
          0.3965*temp_c*math.pow(wind_speed_kmh, 0.16))
    
    return WC


def calculate_wet_bulb_temperature(temp_c: float, humidity: float, pressure_hpa: float = 1013.25) -> float:
    """
    Calculate wet bulb temperature using Stull's formula.
    
    Wet bulb temperature is critical for:
    - Heat stress assessment
    - HVAC calculations
    - Agricultural planning
    
    Args:
        temp_c: Temperature in Celsius
        humidity: Relative humidity (0-100)
        pressure_hpa: Atmospheric pressure in hPa (default: sea level)
    
    Returns:
        Wet bulb temperature in Celsius
    """
    T = temp_c
    RH = humidity
    
    # Stull's formula (simplified, accurate within 1°C)
    Tw = (T * math.atan(0.151977 * math.sqrt(RH + 8.313659)) +
          math.atan(T + RH) - math.atan(RH - 1.676331) +
          0.00391838 * math.pow(RH, 1.5) * math.atan(0.023101 * RH) - 4.686035)
    
    return Tw


# ==================== RISK SCORING ====================

def calculate_fire_risk_score(
    temp_c: float,
    humidity: float,
    wind_speed_kmh: float,
    precipitation_mm: float = 0,
    days_since_rain: int = 0
) -> Dict[str, any]:
    """
    Calculate fire risk score based on weather conditions.
    
    Returns score 0-100 where:
    - 0-20: Low risk
    - 21-40: Moderate risk
    - 41-60: High risk
    - 61-80: Very high risk
    - 81-100: Extreme risk
    
    Args:
        temp_c: Temperature in Celsius
        humidity: Relative humidity (0-100)
        wind_speed_kmh: Wind speed in km/h
        precipitation_mm: Recent precipitation
        days_since_rain: Days since last significant rain
    
    Returns:
        Dict with score, category, and recommendations
    """
    score = 0
    
    # Temperature factor (0-30 points)
    if temp_c > 35:
        score += 30
    elif temp_c > 30:
        score += 25
    elif temp_c > 25:
        score += 15
    elif temp_c > 20:
        score += 5
    
    # Humidity factor (0-30 points)
    if humidity < 20:
        score += 30
    elif humidity < 30:
        score += 25
    elif humidity < 40:
        score += 15
    elif humidity < 50:
        score += 5
    
    # Wind factor (0-20 points)
    if wind_speed_kmh > 40:
        score += 20
    elif wind_speed_kmh > 30:
        score += 15
    elif wind_speed_kmh > 20:
        score += 10
    elif wind_speed_kmh > 10:
        score += 5
    
    # Dryness factor (0-20 points)
    if precipitation_mm == 0:
        if days_since_rain > 14:
            score += 20
        elif days_since_rain > 7:
            score += 15
        elif days_since_rain > 3:
            score += 10
    else:
        score = max(0, score - 10)  # Recent rain reduces risk
    
    # Determine category
    if score >= 81:
        category = "extreme"
        recommendation = "Extreme fire danger. No outdoor burning. Be prepared for rapid fire spread."
    elif score >= 61:
        category = "very_high"
        recommendation = "Very high fire danger. Avoid any open flames. Monitor fire alerts closely."
    elif score >= 41:
        category = "high"
        recommendation = "High fire danger. Exercise caution with any heat sources."
    elif score >= 21:
        category = "moderate"
        recommendation = "Moderate fire danger. Be cautious with outdoor activities involving fire."
    else:
        category = "low"
        recommendation = "Low fire danger. Normal precautions apply."
    
    return {
        "score": min(100, score),
        "category": category,
        "recommendation": recommendation
    }


def calculate_uv_exposure_score(uv_index: float, cloud_cover: float, time_of_day: Optional[str] = None) -> Dict[str, any]:
    """
    Calculate UV exposure risk with recommendations.
    
    Considers UV index and cloud cover for accurate assessment.
    
    Args:
        uv_index: UV index value (0-11+)
        cloud_cover: Cloud cover percentage (0-100)
        time_of_day: Optional time string for additional context
    
    Returns:
        Dict with risk level and protection recommendations
    """
    # Adjust UV for cloud cover (clouds reduce UV by ~20-90% depending on thickness)
    adjusted_uv = uv_index * (1 - (cloud_cover / 100) * 0.5)
    
    if adjusted_uv >= 11:
        level = "extreme"
        color = "violet"
        recommendation = "Extreme risk. Avoid sun exposure 10am-4pm. Sunscreen SPF 50+, protective clothing required."
        minutes_to_burn = 10
    elif adjusted_uv >= 8:
        level = "very_high"
        color = "red"
        recommendation = "Very high risk. Minimize sun exposure. Sunscreen SPF 30+, hat, and sunglasses required."
        minutes_to_burn = 15
    elif adjusted_uv >= 6:
        level = "high"
        color = "orange"
        recommendation = "High risk. Seek shade during midday. Sunscreen SPF 30+, protective clothing advised."
        minutes_to_burn = 20
    elif adjusted_uv >= 3:
        level = "moderate"
        color = "yellow"
        recommendation = "Moderate risk. Use sunscreen SPF 15+. Wear sunglasses on bright days."
        minutes_to_burn = 30
    else:
        level = "low"
        color = "green"
        recommendation = "Low risk. Minimal protection needed. Sunglasses recommended if bright."
        minutes_to_burn = 60
    
    return {
        "uv_index": uv_index,
        "adjusted_uv": round(adjusted_uv, 1),
        "level": level,
        "color": color,
        "minutes_to_burn": minutes_to_burn,
        "recommendation": recommendation
    }


def calculate_travel_disruption_risk(
    precipitation_mm: float,
    wind_speed_kmh: float,
    visibility_m: float,
    temp_c: float,
    weather_code: int
) -> Dict[str, any]:
    """
    Calculate travel disruption risk score.
    
    Useful for:
    - Aviation
    - Road transport
    - Maritime operations
    - Event planning
    
    Args:
        precipitation_mm: Precipitation amount
        wind_speed_kmh: Wind speed
        visibility_m: Visibility in meters
        temp_c: Temperature in Celsius
        weather_code: WMO weather code
    
    Returns:
        Dict with risk score, category, and affected modes
    """
    score = 0
    affected_modes = []
    
    # Precipitation impact
    if precipitation_mm > 50:
        score += 40
        affected_modes.extend(["road", "rail", "air"])
    elif precipitation_mm > 20:
        score += 25
        affected_modes.extend(["road", "rail"])
    elif precipitation_mm > 5:
        score += 10
        affected_modes.append("road")
    
    # Wind impact
    if wind_speed_kmh > 75:
        score += 30
        affected_modes.extend(["air", "maritime", "road"])
    elif wind_speed_kmh > 50:
        score += 20
        affected_modes.extend(["air", "maritime"])
    elif wind_speed_kmh > 30:
        score += 10
        affected_modes.append("maritime")
    
    # Visibility impact
    if visibility_m < 100:
        score += 30
        affected_modes.extend(["road", "air", "maritime"])
    elif visibility_m < 500:
        score += 20
        affected_modes.extend(["road", "air"])
    elif visibility_m < 1000:
        score += 10
        affected_modes.append("road")
    
    # Temperature impact (ice/snow)
    if temp_c < -10:
        score += 15
        affected_modes.extend(["road", "rail"])
    elif temp_c < 0:
        score += 10
        affected_modes.append("road")
    
    # Severe weather codes (thunderstorms, snow, etc.)
    severe_codes = [95, 96, 99, 71, 73, 75, 77, 85, 86]
    if weather_code in severe_codes:
        score += 20
        affected_modes = list(set(affected_modes + ["road", "rail", "air"]))
    
    # Determine category
    score = min(100, score)
    if score >= 70:
        category = "severe"
        recommendation = "Severe disruption expected. Avoid all non-essential travel."
    elif score >= 50:
        category = "major"
        recommendation = "Major disruption likely. Delay travel if possible."
    elif score >= 30:
        category = "moderate"
        recommendation = "Moderate disruption possible. Allow extra time and check conditions."
    elif score >= 10:
        category = "minor"
        recommendation = "Minor delays possible. Exercise normal caution."
    else:
        category = "minimal"
        recommendation = "Minimal disruption expected. Normal conditions."
    
    return {
        "score": score,
        "category": category,
        "affected_modes": list(set(affected_modes)),
        "recommendation": recommendation
    }


def calculate_rain_confidence(
    precipitation_probability: float,
    precipitation_mm: float,
    cloud_cover: float,
    humidity: float
) -> Dict[str, any]:
    """
    Calculate rain probability confidence score.
    
    Combines multiple factors to assess how confident we can be
    in the precipitation forecast.
    
    Args:
        precipitation_probability: Forecast probability (0-100)
        precipitation_mm: Forecast amount in mm
        cloud_cover: Cloud cover percentage (0-100)
        humidity: Relative humidity (0-100)
    
    Returns:
        Dict with confidence score and interpretation
    """
    confidence = 0
    
    # Base confidence from reported probability
    if precipitation_probability >= 80:
        confidence = 85
    elif precipitation_probability >= 60:
        confidence = 70
    elif precipitation_probability >= 40:
        confidence = 55
    elif precipitation_probability >= 20:
        confidence = 40
    else:
        confidence = 30
    
    # Adjust for supporting conditions
    if cloud_cover > 80 and humidity > 70:
        confidence += 10  # Strong support
    elif cloud_cover > 60 and humidity > 60:
        confidence += 5  # Moderate support
    elif cloud_cover < 30 or humidity < 40:
        confidence -= 10  # Contradictory conditions
    
    # Adjust for forecast amount
    if precipitation_mm > 10:
        confidence += 5  # Significant amount increases confidence
    elif precipitation_mm > 0 and precipitation_mm < 1:
        confidence -= 5  # Small amounts are less certain
    
    confidence = max(0, min(100, confidence))
    
    # Interpretation
    if confidence >= 80:
        interpretation = "Very high confidence in forecast"
    elif confidence >= 60:
        interpretation = "High confidence in forecast"
    elif confidence >= 40:
        interpretation = "Moderate confidence in forecast"
    else:
        interpretation = "Low confidence in forecast"
    
    return {
        "confidence_score": confidence,
        "interpretation": interpretation,
        "precipitation_probability": precipitation_probability,
        "supporting_factors": {
            "cloud_cover": cloud_cover,
            "humidity": humidity,
            "forecast_amount_mm": precipitation_mm
        }
    }


# ==================== COMFORT INDICES ====================

def calculate_comfort_index(temp_c: float, humidity: float, wind_speed_kmh: float) -> Dict[str, any]:
    """
    Calculate overall comfort index combining multiple factors.
    
    Returns comfort score 0-100 where:
    - 80-100: Very comfortable
    - 60-79: Comfortable
    - 40-59: Moderate
    - 20-39: Uncomfortable
    - 0-19: Very uncomfortable
    """
    score = 50  # Start at neutral
    
    # Temperature comfort (optimal: 18-24°C)
    if 18 <= temp_c <= 24:
        score += 25
    elif 15 <= temp_c < 18 or 24 < temp_c <= 28:
        score += 15
    elif 10 <= temp_c < 15 or 28 < temp_c <= 32:
        score += 5
    elif temp_c < 0 or temp_c > 38:
        score -= 20
    else:
        score -= 10
    
    # Humidity comfort (optimal: 40-60%)
    if 40 <= humidity <= 60:
        score += 15
    elif 30 <= humidity < 40 or 60 < humidity <= 70:
        score += 5
    elif humidity < 20 or humidity > 80:
        score -= 15
    else:
        score -= 5
    
    # Wind comfort (light breeze is pleasant)
    if 5 <= wind_speed_kmh <= 15:
        score += 10
    elif wind_speed_kmh > 40:
        score -= 15
    elif wind_speed_kmh > 30:
        score -= 10
    
    score = max(0, min(100, score))
    
    # Category
    if score >= 80:
        category = "very_comfortable"
        description = "Excellent conditions for outdoor activities"
    elif score >= 60:
        category = "comfortable"
        description = "Pleasant conditions"
    elif score >= 40:
        category = "moderate"
        description = "Tolerable conditions"
    elif score >= 20:
        category = "uncomfortable"
        description = "Uncomfortable conditions, limit outdoor exposure"
    else:
        category = "very_uncomfortable"
        description = "Very uncomfortable conditions, avoid prolonged outdoor exposure"
    
    return {
        "score": score,
        "category": category,
        "description": description
    }


# ==================== COMPREHENSIVE INSIGHTS ====================

def calculate_all_insights(weather_data: Dict) -> Dict:
    """
    Calculate all available weather insights from raw weather data.
    
    Args:
        weather_data: Dict containing weather parameters
    
    Returns:
        Dict with all calculated insights
    """
    insights = {}
    
    temp = weather_data.get("temperature_2m")
    humidity = weather_data.get("relative_humidity_2m")
    wind_speed = weather_data.get("wind_speed_10m")
    precipitation = weather_data.get("precipitation", 0)
    pressure = weather_data.get("pressure_msl", 1013.25)
    cloud_cover = weather_data.get("cloud_cover", 0)
    uv_index = weather_data.get("uv_index", 0)
    visibility = weather_data.get("visibility", 10000)
    weather_code = weather_data.get("weather_code", 0)
    precip_prob = weather_data.get("precipitation_probability", 0)
    
    if temp is not None and humidity is not None:
        # Temperature feels-like
        if temp > 27:
            insights["heat_index"] = calculate_heat_index(temp, humidity)
        if temp < 10 and wind_speed:
            insights["wind_chill"] = calculate_wind_chill(temp, wind_speed)
        
        insights["wet_bulb_temperature"] = calculate_wet_bulb_temperature(temp, humidity, pressure)
        
        # Comfort index
        if wind_speed is not None:
            insights["comfort"] = calculate_comfort_index(temp, humidity, wind_speed)
    
    # Fire risk
    if all(v is not None for v in [temp, humidity, wind_speed]):
        insights["fire_risk"] = calculate_fire_risk_score(temp, humidity, wind_speed, precipitation)
    
    # UV exposure
    if uv_index is not None:
        insights["uv_exposure"] = calculate_uv_exposure_score(uv_index, cloud_cover)
    
    # Travel disruption
    if all(v is not None for v in [precipitation, wind_speed, visibility, temp, weather_code]):
        insights["travel_disruption"] = calculate_travel_disruption_risk(
            precipitation, wind_speed, visibility, temp, weather_code
        )
    
    # Rain confidence
    if all(v is not None for v in [precip_prob, precipitation, cloud_cover, humidity]):
        insights["rain_confidence"] = calculate_rain_confidence(
            precip_prob, precipitation, cloud_cover, humidity
        )
    
    return insights
