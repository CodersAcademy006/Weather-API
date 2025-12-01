"""
Solar & Energy Weather Module

Provides comprehensive solar energy data including:
- Solar irradiance (GHI, DNI, DHI)
- Photovoltaic (PV) yield estimation
- Sun position (azimuth, elevation)
- Cloud-adjusted solar radiation
- Day/night cycles and twilight
- Solar energy potential scoring

Data sources:
- Open-Meteo Solar Radiation API (free)
- NASA POWER API (alternative/backup)
- Astronomical calculations for sun position
"""

import requests
import math
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum


class SkyCondition(str, Enum):
    """Sky condition classifications"""
    CLEAR = "clear"
    MOSTLY_CLEAR = "mostly_clear"
    PARTLY_CLOUDY = "partly_cloudy"
    MOSTLY_CLOUDY = "mostly_cloudy"
    OVERCAST = "overcast"


class SolarPotential(str, Enum):
    """Solar energy potential ratings"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    VERY_POOR = "very_poor"


def calculate_sun_position(latitude: float, longitude: float, timestamp: datetime) -> Dict[str, Any]:
    """
    Calculate sun position (azimuth and elevation) for given location and time
    
    Uses astronomical formulas from NOAA Solar Calculator
    
    Args:
        latitude: Location latitude in degrees
        longitude: Location longitude in degrees
        timestamp: UTC datetime
        
    Returns:
        Dictionary with sun azimuth, elevation, and related data
    """
    
    # Convert to radians
    lat_rad = math.radians(latitude)
    
    # Calculate Julian Day
    a = (14 - timestamp.month) // 12
    y = timestamp.year + 4800 - a
    m = timestamp.month + 12 * a - 3
    
    jd = timestamp.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    jd += (timestamp.hour - 12) / 24 + timestamp.minute / 1440 + timestamp.second / 86400
    
    # Calculate Julian Century
    jc = (jd - 2451545) / 36525
    
    # Calculate sun declination
    mean_long = (280.46646 + jc * (36000.76983 + jc * 0.0003032)) % 360
    mean_anom = 357.52911 + jc * (35999.05029 - 0.0001537 * jc)
    mean_anom_rad = math.radians(mean_anom)
    
    sun_eq = math.sin(mean_anom_rad) * (1.914602 - jc * (0.004817 + 0.000014 * jc)) + \
             math.sin(2 * mean_anom_rad) * (0.019993 - 0.000101 * jc) + \
             math.sin(3 * mean_anom_rad) * 0.000289
    
    sun_true_long = mean_long + sun_eq
    sun_app_long = sun_true_long - 0.00569 - 0.00478 * math.sin(math.radians(125.04 - 1934.136 * jc))
    
    obliq_corr = 23 + (26 + ((21.448 - jc * (46.815 + jc * (0.00059 - jc * 0.001813)))) / 60) / 60
    obliq_corr += 0.00256 * math.cos(math.radians(125.04 - 1934.136 * jc))
    
    sun_decl = math.degrees(math.asin(math.sin(math.radians(obliq_corr)) * math.sin(math.radians(sun_app_long))))
    sun_decl_rad = math.radians(sun_decl)
    
    # Calculate equation of time
    var_y = math.tan(math.radians(obliq_corr / 2)) ** 2
    eq_of_time = 4 * math.degrees(
        var_y * math.sin(2 * math.radians(mean_long)) -
        2 * math.radians(mean_anom) * var_y +
        4 * math.radians(mean_anom) * var_y * math.sin(2 * math.radians(mean_long)) -
        0.5 * var_y * var_y * math.sin(4 * math.radians(mean_long)) -
        1.25 * mean_anom_rad * mean_anom_rad
    )
    
    # Calculate hour angle
    true_solar_time = (timestamp.hour * 60 + timestamp.minute + timestamp.second / 60 + eq_of_time + 4 * longitude) % 1440
    hour_angle = (true_solar_time / 4 - 180) if true_solar_time < 0 else (true_solar_time / 4 - 180)
    hour_angle_rad = math.radians(hour_angle)
    
    # Calculate solar elevation
    solar_elevation_rad = math.asin(
        math.sin(lat_rad) * math.sin(sun_decl_rad) +
        math.cos(lat_rad) * math.cos(sun_decl_rad) * math.cos(hour_angle_rad)
    )
    solar_elevation = math.degrees(solar_elevation_rad)
    
    # Calculate solar azimuth
    solar_azimuth_rad = math.acos(
        (math.sin(sun_decl_rad) * math.cos(lat_rad) -
         math.cos(sun_decl_rad) * math.sin(lat_rad) * math.cos(hour_angle_rad)) /
        math.cos(solar_elevation_rad)
    ) if solar_elevation_rad != 0 else 0
    
    solar_azimuth = math.degrees(solar_azimuth_rad)
    if hour_angle > 0:
        solar_azimuth = 360 - solar_azimuth
    
    # Atmospheric refraction correction
    if solar_elevation > -0.833:
        refraction = 0
        if solar_elevation <= 85:
            te = math.tan(math.radians(solar_elevation))
            if solar_elevation > 5:
                refraction = 58.1 / te - 0.07 / (te ** 3) + 0.000086 / (te ** 5)
            elif solar_elevation > -0.575:
                refraction = 1735 + solar_elevation * (-518.2 + solar_elevation * (103.4 + solar_elevation * (-12.79 + solar_elevation * 0.711)))
            else:
                refraction = -20.772 / te
            refraction /= 3600
        solar_elevation += refraction
    
    return {
        "azimuth_deg": round(solar_azimuth, 2),
        "elevation_deg": round(solar_elevation, 2),
        "is_daylight": solar_elevation > -6,  # Civil twilight
        "is_direct_sun": solar_elevation > 0,
        "zenith_angle_deg": round(90 - solar_elevation, 2)
    }


def calculate_daylight_info(latitude: float, longitude: float, date: datetime.date) -> Dict[str, Any]:
    """
    Calculate sunrise, sunset, and daylight duration
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
        date: Date for calculation
        
    Returns:
        Sunrise, sunset, and daylight information
    """
    
    # Simplified calculation - scan through the day
    sunrise = None
    sunset = None
    
    for hour in range(24):
        for minute in [0, 30]:
            dt = datetime(date.year, date.month, date.day, hour, minute, 0)
            sun_pos = calculate_sun_position(latitude, longitude, dt)
            
            if sun_pos["elevation_deg"] > 0:
                if sunrise is None:
                    sunrise = dt
                sunset = dt
    
    if sunrise and sunset:
        daylight_hours = (sunset - sunrise).total_seconds() / 3600
    else:
        daylight_hours = 0
    
    # Calculate solar noon (when sun is highest)
    solar_noon = None
    max_elevation = -90
    for hour in range(24):
        dt = datetime(date.year, date.month, date.day, hour, 0, 0)
        sun_pos = calculate_sun_position(latitude, longitude, dt)
        if sun_pos["elevation_deg"] > max_elevation:
            max_elevation = sun_pos["elevation_deg"]
            solar_noon = dt
    
    return {
        "sunrise": sunrise.isoformat() + "Z" if sunrise else None,
        "sunset": sunset.isoformat() + "Z" if sunset else None,
        "solar_noon": solar_noon.isoformat() + "Z" if solar_noon else None,
        "daylight_hours": round(daylight_hours, 2),
        "max_elevation_deg": round(max_elevation, 2)
    }


def estimate_pv_yield(
    ghi: float,
    dni: float,
    dhi: float,
    temperature: float,
    panel_efficiency: float = 0.20,
    system_loss: float = 0.14
) -> Dict[str, Any]:
    """
    Estimate photovoltaic (PV) power yield
    
    Args:
        ghi: Global Horizontal Irradiance (W/m²)
        dni: Direct Normal Irradiance (W/m²)
        dhi: Diffuse Horizontal Irradiance (W/m²)
        temperature: Ambient temperature (°C)
        panel_efficiency: Solar panel efficiency (default: 20% for modern panels)
        system_loss: System losses (default: 14% - inverter, wiring, soiling)
        
    Returns:
        PV yield estimates in W/m² and kWh/m²/day
    """
    
    # Temperature coefficient (typical: -0.4%/°C above 25°C)
    temp_coefficient = -0.004
    temp_loss = 1 + temp_coefficient * (temperature - 25) if temperature > 25 else 1
    
    # Calculate effective irradiance accounting for temperature
    effective_irradiance = ghi * temp_loss
    
    # Calculate power output (W/m²)
    power_output = effective_irradiance * panel_efficiency * (1 - system_loss)
    
    # Estimate daily energy (kWh/m²/day) - rough estimate
    # Assuming this is peak hour value, multiply by average sun hours
    daily_energy = power_output * 5 / 1000  # Rough estimate: 5 peak sun hours
    
    return {
        "instantaneous_power_w_per_m2": round(power_output, 2),
        "estimated_daily_kwh_per_m2": round(daily_energy, 3),
        "efficiency_factors": {
            "panel_efficiency": panel_efficiency,
            "system_loss": system_loss,
            "temperature_derating": round(temp_loss, 3)
        }
    }


def assess_solar_potential(ghi: float, cloud_cover: float) -> Dict[str, Any]:
    """
    Assess solar energy potential based on irradiance and cloud cover
    
    Args:
        ghi: Global Horizontal Irradiance (W/m²)
        cloud_cover: Cloud cover percentage (0-100)
        
    Returns:
        Solar potential rating and score
    """
    
    # Calculate base score from GHI (max ~1000 W/m²)
    ghi_score = min(100, (ghi / 1000) * 100)
    
    # Cloud cover penalty
    cloud_penalty = cloud_cover * 0.8  # Up to 80% reduction for full cloud
    
    # Final score
    final_score = max(0, ghi_score - cloud_penalty)
    
    # Classify potential
    if final_score >= 80:
        potential = SolarPotential.EXCELLENT
        description = "Excellent solar conditions - ideal for PV generation"
    elif final_score >= 60:
        potential = SolarPotential.GOOD
        description = "Good solar conditions - favorable for PV generation"
    elif final_score >= 40:
        potential = SolarPotential.FAIR
        description = "Fair solar conditions - moderate PV generation expected"
    elif final_score >= 20:
        potential = SolarPotential.POOR
        description = "Poor solar conditions - limited PV generation"
    else:
        potential = SolarPotential.VERY_POOR
        description = "Very poor solar conditions - minimal PV generation"
    
    # Classify sky condition
    if cloud_cover < 10:
        sky = SkyCondition.CLEAR
    elif cloud_cover < 30:
        sky = SkyCondition.MOSTLY_CLEAR
    elif cloud_cover < 60:
        sky = SkyCondition.PARTLY_CLOUDY
    elif cloud_cover < 85:
        sky = SkyCondition.MOSTLY_CLOUDY
    else:
        sky = SkyCondition.OVERCAST
    
    return {
        "potential": potential,
        "score": round(final_score, 1),
        "description": description,
        "sky_condition": sky,
        "ghi_score": round(ghi_score, 1),
        "cloud_penalty": round(cloud_penalty, 1)
    }


async def fetch_solar_radiation_data(latitude: float, longitude: float, days: int = 7) -> Dict[str, Any]:
    """
    Fetch solar radiation data from Open-Meteo
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
        days: Number of forecast days
        
    Returns:
        Solar radiation data
    """
    
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ",".join([
                "shortwave_radiation",
                "direct_radiation",
                "diffuse_radiation",
                "direct_normal_irradiance",
                "global_tilted_irradiance",
                "temperature_2m",
                "cloud_cover"
            ]),
            "daily": "shortwave_radiation_sum,sunshine_duration",
            "forecast_days": min(days, 16),
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


async def get_current_solar_conditions(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Get current solar radiation and energy conditions
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
        
    Returns:
        Current solar conditions with PV yield estimates
    """
    
    # Fetch solar data
    solar_data = await fetch_solar_radiation_data(latitude, longitude, days=1)
    
    if "error" in solar_data:
        return {
            "status": "unavailable",
            "message": "Solar data temporarily unavailable",
            "latitude": latitude,
            "longitude": longitude
        }
    
    hourly = solar_data.get("hourly", {})
    times = hourly.get("time", [])
    
    if not times:
        return {
            "status": "no_data",
            "message": "No solar data available",
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
    ghi = hourly.get("shortwave_radiation", [0] * len(times))[current_index] or 0  # W/m²
    dni = hourly.get("direct_normal_irradiance", [0] * len(times))[current_index] or 0
    dhi = hourly.get("diffuse_radiation", [0] * len(times))[current_index] or 0
    temperature = hourly.get("temperature_2m", [20] * len(times))[current_index] or 20
    cloud_cover = hourly.get("cloud_cover", [0] * len(times))[current_index] or 0
    
    # Calculate sun position
    sun_position = calculate_sun_position(latitude, longitude, now)
    
    # Estimate PV yield
    pv_yield = estimate_pv_yield(ghi, dni, dhi, temperature)
    
    # Assess solar potential
    solar_assessment = assess_solar_potential(ghi, cloud_cover)
    
    # Calculate daylight info
    daylight_info = calculate_daylight_info(latitude, longitude, now.date())
    
    return {
        "status": "success",
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": times[current_index],
        "sun_position": sun_position,
        "irradiance": {
            "ghi_w_per_m2": round(ghi, 2),
            "dni_w_per_m2": round(dni, 2),
            "dhi_w_per_m2": round(dhi, 2),
            "note": "GHI=Global Horizontal, DNI=Direct Normal, DHI=Diffuse Horizontal"
        },
        "pv_yield_estimate": pv_yield,
        "solar_potential": solar_assessment,
        "daylight": daylight_info,
        "conditions": {
            "temperature_c": round(temperature, 1),
            "cloud_cover_pct": round(cloud_cover, 1)
        },
        "metadata": {
            "source": "Open-Meteo Weather API",
            "pv_assumptions": "20% panel efficiency, 14% system losses"
        }
    }


async def get_daily_solar_forecast(latitude: float, longitude: float, days: int = 7) -> Dict[str, Any]:
    """
    Get daily solar energy forecast
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
        days: Number of forecast days
        
    Returns:
        Daily solar forecast with energy estimates
    """
    
    solar_data = await fetch_solar_radiation_data(latitude, longitude, days)
    
    if "error" in solar_data:
        return {
            "status": "unavailable",
            "message": "Solar forecast temporarily unavailable"
        }
    
    daily = solar_data.get("daily", {})
    dates = daily.get("time", [])
    
    if not dates:
        return {
            "status": "no_data",
            "message": "No solar forecast available"
        }
    
    hourly = solar_data.get("hourly", {})
    hourly_times = hourly.get("time", [])
    
    forecast = []
    
    for i, date_str in enumerate(dates):
        # Get daily aggregates
        total_radiation = daily.get("shortwave_radiation_sum", [0] * len(dates))[i] or 0  # MJ/m²
        sunshine_duration = daily.get("sunshine_duration", [0] * len(dates))[i] or 0  # seconds
        
        # Convert to kWh/m²
        daily_kwh = total_radiation * 0.277778  # 1 MJ = 0.277778 kWh
        
        # Calculate daylight info for this day
        date_obj = datetime.fromisoformat(date_str).date()
        daylight_info = calculate_daylight_info(latitude, longitude, date_obj)
        
        # Find peak hour data for this day
        peak_ghi = 0
        peak_cloud_cover = 0
        
        for j, time_str in enumerate(hourly_times):
            if time_str.startswith(date_str):
                ghi = hourly.get("shortwave_radiation", [0] * len(hourly_times))[j] or 0
                if ghi > peak_ghi:
                    peak_ghi = ghi
                    peak_cloud_cover = hourly.get("cloud_cover", [0] * len(hourly_times))[j] or 0
        
        # Assess potential
        solar_assessment = assess_solar_potential(peak_ghi, peak_cloud_cover)
        
        # Estimate PV production (kWh/m²/day)
        # Apply efficiency and losses to daily radiation
        pv_production = daily_kwh * 0.20 * 0.86  # 20% efficiency, 14% losses
        
        forecast.append({
            "date": date_str,
            "total_radiation_kwh_per_m2": round(daily_kwh, 2),
            "sunshine_hours": round(sunshine_duration / 3600, 2),
            "peak_irradiance_w_per_m2": round(peak_ghi, 2),
            "estimated_pv_yield_kwh_per_m2": round(pv_production, 3),
            "solar_potential": solar_assessment,
            "daylight": daylight_info
        })
    
    return {
        "status": "success",
        "latitude": latitude,
        "longitude": longitude,
        "forecast_days": len(forecast),
        "daily_forecast": forecast,
        "metadata": {
            "source": "Open-Meteo Weather API",
            "pv_assumptions": "20% panel efficiency, 14% system losses"
        }
    }
