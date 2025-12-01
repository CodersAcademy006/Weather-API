"""
Extended Air Quality Module (AQI V2)

Provides comprehensive air quality data including:
- Detailed pollutant concentrations (PM1, PM2.5, PM10, NO₂, SO₂, CO, O₃)
- Air Quality Index (AQI) calculations (US EPA and European standards)
- Health guidance and exposure scoring
- Pollutant-specific health impacts
- Sensitive group warnings
- Outdoor activity recommendations

Data sources:
- Open-Meteo Air Quality API (free)
- Real-time pollutant monitoring
"""

import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum


class AQILevel(str, Enum):
    """US EPA Air Quality Index levels"""
    GOOD = "good"
    MODERATE = "moderate"
    UNHEALTHY_SENSITIVE = "unhealthy_for_sensitive_groups"
    UNHEALTHY = "unhealthy"
    VERY_UNHEALTHY = "very_unhealthy"
    HAZARDOUS = "hazardous"


class EuropeanAQILevel(str, Enum):
    """European Air Quality Index levels"""
    VERY_GOOD = "very_good"
    GOOD = "good"
    MEDIUM = "medium"
    POOR = "poor"
    VERY_POOR = "very_poor"
    EXTREMELY_POOR = "extremely_poor"


def calculate_us_epa_aqi(pollutant: str, concentration: float) -> Dict[str, Any]:
    """
    Calculate US EPA Air Quality Index for a specific pollutant
    
    Args:
        pollutant: Pollutant name (pm25, pm10, o3, no2, so2, co)
        concentration: Concentration in µg/m³
        
    Returns:
        AQI value and category
    """
    
    # US EPA AQI breakpoints [C_low, C_high, I_low, I_high]
    breakpoints = {
        "pm25": [  # 24-hour average, µg/m³
            (0.0, 12.0, 0, 50),
            (12.1, 35.4, 51, 100),
            (35.5, 55.4, 101, 150),
            (55.5, 150.4, 151, 200),
            (150.5, 250.4, 201, 300),
            (250.5, 500.4, 301, 500)
        ],
        "pm10": [  # 24-hour average, µg/m³
            (0, 54, 0, 50),
            (55, 154, 51, 100),
            (155, 254, 101, 150),
            (255, 354, 151, 200),
            (355, 424, 201, 300),
            (425, 604, 301, 500)
        ],
        "o3": [  # 8-hour average, ppb converted to µg/m³ (multiply ppb by 2)
            (0, 108, 0, 50),
            (109, 140, 51, 100),
            (141, 170, 101, 150),
            (171, 210, 151, 200),
            (211, 400, 201, 300)
        ],
        "no2": [  # 1-hour average, ppb converted to µg/m³ (multiply ppb by 1.88)
            (0, 100, 0, 50),
            (101, 360, 51, 100),
            (361, 649, 101, 150),
            (650, 1249, 151, 200),
            (1250, 2049, 201, 300)
        ],
        "so2": [  # 1-hour average, ppb converted to µg/m³ (multiply ppb by 2.62)
            (0, 91, 0, 50),
            (92, 196, 51, 100),
            (197, 484, 101, 150),
            (485, 797, 151, 200),
            (798, 1582, 201, 300)
        ],
        "co": [  # 8-hour average, mg/m³ (concentration already in mg/m³)
            (0, 4.4, 0, 50),
            (4.5, 9.4, 51, 100),
            (9.5, 12.4, 101, 150),
            (12.5, 15.4, 151, 200),
            (15.5, 30.4, 201, 300)
        ]
    }
    
    if pollutant not in breakpoints:
        return {"aqi": 0, "level": AQILevel.GOOD, "error": f"Unknown pollutant: {pollutant}"}
    
    # Find appropriate breakpoint
    for c_low, c_high, i_low, i_high in breakpoints[pollutant]:
        if c_low <= concentration <= c_high:
            # Linear interpolation
            aqi = ((i_high - i_low) / (c_high - c_low)) * (concentration - c_low) + i_low
            aqi = round(aqi)
            
            # Determine level
            if aqi <= 50:
                level = AQILevel.GOOD
            elif aqi <= 100:
                level = AQILevel.MODERATE
            elif aqi <= 150:
                level = AQILevel.UNHEALTHY_SENSITIVE
            elif aqi <= 200:
                level = AQILevel.UNHEALTHY
            elif aqi <= 300:
                level = AQILevel.VERY_UNHEALTHY
            else:
                level = AQILevel.HAZARDOUS
            
            return {
                "aqi": aqi,
                "level": level,
                "concentration": round(concentration, 2)
            }
    
    # Concentration beyond breakpoints - hazardous
    return {
        "aqi": 500,
        "level": AQILevel.HAZARDOUS,
        "concentration": round(concentration, 2)
    }


def calculate_european_aqi(pollutants: Dict[str, float]) -> Dict[str, Any]:
    """
    Calculate European Air Quality Index (EAQI)
    
    Args:
        pollutants: Dictionary of pollutant concentrations
        
    Returns:
        European AQI value and category
    """
    
    # European AQI bands for each pollutant (µg/m³)
    bands = {
        "pm25": [(0, 10), (10, 20), (20, 25), (25, 50), (50, 75), (75, 800)],
        "pm10": [(0, 20), (20, 40), (40, 50), (50, 100), (100, 150), (150, 1200)],
        "no2": [(0, 40), (40, 90), (90, 120), (120, 230), (230, 340), (340, 1000)],
        "o3": [(0, 50), (50, 100), (100, 130), (130, 240), (240, 380), (380, 800)],
        "so2": [(0, 100), (100, 200), (200, 350), (350, 500), (500, 750), (750, 1250)]
    }
    
    max_index = 1
    worst_pollutant = None
    
    for pollutant, concentration in pollutants.items():
        if pollutant in bands:
            for i, (low, high) in enumerate(bands[pollutant]):
                if low <= concentration < high:
                    index = i + 1
                    if index > max_index:
                        max_index = index
                        worst_pollutant = pollutant
                    break
            else:
                # Beyond all bands
                if concentration >= bands[pollutant][-1][1]:
                    max_index = 6
                    worst_pollutant = pollutant
    
    # Map index to level
    levels = [
        EuropeanAQILevel.VERY_GOOD,
        EuropeanAQILevel.GOOD,
        EuropeanAQILevel.MEDIUM,
        EuropeanAQILevel.POOR,
        EuropeanAQILevel.VERY_POOR,
        EuropeanAQILevel.EXTREMELY_POOR
    ]
    
    level = levels[min(max_index - 1, 5)]
    
    return {
        "index": max_index,
        "level": level,
        "worst_pollutant": worst_pollutant
    }


def get_health_guidance(aqi: int, level: AQILevel) -> Dict[str, Any]:
    """
    Get health guidance based on AQI level
    
    Args:
        aqi: Air Quality Index value
        level: AQI level category
        
    Returns:
        Health guidance and recommendations
    """
    
    if level == AQILevel.GOOD:
        return {
            "message": "Air quality is excellent. Ideal for outdoor activities.",
            "general_population": "No health implications",
            "sensitive_groups": "No precautions needed",
            "outdoor_activities": "Unlimited outdoor activities recommended",
            "color": "#00E400"
        }
    elif level == AQILevel.MODERATE:
        return {
            "message": "Air quality is acceptable for most people.",
            "general_population": "No restrictions on outdoor activities",
            "sensitive_groups": "Unusually sensitive individuals should consider reducing prolonged outdoor exertion",
            "outdoor_activities": "Normal outdoor activities acceptable",
            "color": "#FFFF00"
        }
    elif level == AQILevel.UNHEALTHY_SENSITIVE:
        return {
            "message": "Sensitive groups may experience health effects.",
            "general_population": "General public not likely affected",
            "sensitive_groups": "People with respiratory/heart disease, children, older adults should reduce prolonged outdoor exertion",
            "outdoor_activities": "Sensitive groups should limit prolonged outdoor activities",
            "color": "#FF7E00"
        }
    elif level == AQILevel.UNHEALTHY:
        return {
            "message": "Everyone may begin to experience health effects.",
            "general_population": "Reduce prolonged or heavy outdoor exertion",
            "sensitive_groups": "Avoid prolonged outdoor exertion. Keep outdoor activities short.",
            "outdoor_activities": "Limit outdoor activities, especially for sensitive groups",
            "color": "#FF0000"
        }
    elif level == AQILevel.VERY_UNHEALTHY:
        return {
            "message": "Health alert: everyone may experience serious health effects.",
            "general_population": "Avoid prolonged outdoor exertion. Move activities indoors or reschedule.",
            "sensitive_groups": "Remain indoors and keep activity levels low",
            "outdoor_activities": "Avoid all outdoor activities",
            "color": "#8F3F97"
        }
    else:  # HAZARDOUS
        return {
            "message": "Health warning of emergency conditions.",
            "general_population": "Remain indoors and keep activity levels low",
            "sensitive_groups": "Remain indoors and avoid all physical activity",
            "outdoor_activities": "All outdoor activities should be avoided",
            "color": "#7E0023"
        }


def get_pollutant_health_impact(pollutant: str, concentration: float) -> Dict[str, Any]:
    """
    Get specific health impacts for individual pollutants
    
    Args:
        pollutant: Pollutant name
        concentration: Concentration value
        
    Returns:
        Health impact information for the pollutant
    """
    
    impacts = {
        "pm25": {
            "name": "Fine Particulate Matter (PM2.5)",
            "size": "≤ 2.5 micrometers",
            "sources": ["Vehicle exhaust", "Industrial emissions", "Wildfires", "Cooking"],
            "health_effects": [
                "Respiratory irritation",
                "Aggravated asthma",
                "Decreased lung function",
                "Cardiovascular effects",
                "Premature death in people with heart/lung disease"
            ],
            "penetration": "Can penetrate deep into lungs and bloodstream"
        },
        "pm10": {
            "name": "Coarse Particulate Matter (PM10)",
            "size": "≤ 10 micrometers",
            "sources": ["Dust", "Pollen", "Mold", "Construction", "Agriculture"],
            "health_effects": [
                "Respiratory irritation",
                "Asthma attacks",
                "Increased respiratory symptoms",
                "Chronic bronchitis"
            ],
            "penetration": "Can penetrate into lungs"
        },
        "no2": {
            "name": "Nitrogen Dioxide (NO₂)",
            "sources": ["Vehicle exhaust", "Power plants", "Industrial facilities"],
            "health_effects": [
                "Respiratory infections",
                "Aggravated asthma",
                "Chronic lung disease",
                "Reduced lung function"
            ],
            "note": "Can react to form PM2.5 and ozone"
        },
        "so2": {
            "name": "Sulfur Dioxide (SO₂)",
            "sources": ["Fossil fuel combustion", "Industrial processes", "Volcanoes"],
            "health_effects": [
                "Respiratory irritation",
                "Breathing difficulties",
                "Aggravated asthma",
                "Cardiovascular effects"
            ],
            "note": "Can react to form particulate matter"
        },
        "co": {
            "name": "Carbon Monoxide (CO)",
            "sources": ["Vehicle exhaust", "Incomplete combustion", "Gas appliances"],
            "health_effects": [
                "Reduced oxygen delivery to organs",
                "Headaches",
                "Dizziness",
                "Confusion",
                "Death at high concentrations"
            ],
            "note": "Colorless, odorless, and deadly"
        },
        "o3": {
            "name": "Ground-level Ozone (O₃)",
            "sources": ["Chemical reaction of NOx and VOCs in sunlight"],
            "health_effects": [
                "Respiratory irritation",
                "Reduced lung function",
                "Aggravated asthma",
                "Lung inflammation",
                "Premature aging of lungs"
            ],
            "note": "Worse on hot, sunny days"
        }
    }
    
    return impacts.get(pollutant, {"name": pollutant.upper(), "health_effects": []})


async def fetch_air_quality_data(latitude: float, longitude: float, days: int = 7) -> Dict[str, Any]:
    """
    Fetch comprehensive air quality data from Open-Meteo
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
        days: Number of forecast days
        
    Returns:
        Air quality data including all pollutants
    """
    
    try:
        url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ",".join([
                "pm10",
                "pm2_5",
                "carbon_monoxide",
                "nitrogen_dioxide",
                "sulphur_dioxide",
                "ozone",
                "dust",
                "uv_index",
                "uv_index_clear_sky",
                "ammonia",
                "aerosol_optical_depth"
            ]),
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


async def get_current_air_quality(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Get current air quality with detailed pollutant breakdown
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
        
    Returns:
        Current air quality data with AQI calculations
    """
    
    # Fetch air quality data
    aq_data = await fetch_air_quality_data(latitude, longitude, days=1)
    
    if "error" in aq_data:
        return {
            "status": "unavailable",
            "message": "Air quality data temporarily unavailable",
            "latitude": latitude,
            "longitude": longitude
        }
    
    hourly = aq_data.get("hourly", {})
    times = hourly.get("time", [])
    
    if not times:
        return {
            "status": "no_data",
            "message": "No air quality data available for this location",
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
    
    # Extract current pollutant concentrations
    pm25 = hourly.get("pm2_5", [0] * len(times))[current_index] or 0
    pm10 = hourly.get("pm10", [0] * len(times))[current_index] or 0
    no2 = hourly.get("nitrogen_dioxide", [0] * len(times))[current_index] or 0
    so2 = hourly.get("sulphur_dioxide", [0] * len(times))[current_index] or 0
    co = hourly.get("carbon_monoxide", [0] * len(times))[current_index] or 0  # µg/m³
    o3 = hourly.get("ozone", [0] * len(times))[current_index] or 0
    dust = hourly.get("dust", [0] * len(times))[current_index] or 0
    uv_index = hourly.get("uv_index", [0] * len(times))[current_index] or 0
    
    # Convert CO from µg/m³ to mg/m³ for US EPA AQI calculation
    co_mg = co / 1000
    
    # Calculate individual AQIs (US EPA)
    aqi_pm25 = calculate_us_epa_aqi("pm25", pm25)
    aqi_pm10 = calculate_us_epa_aqi("pm10", pm10)
    aqi_no2 = calculate_us_epa_aqi("no2", no2)
    aqi_so2 = calculate_us_epa_aqi("so2", so2)
    aqi_co = calculate_us_epa_aqi("co", co_mg)
    aqi_o3 = calculate_us_epa_aqi("o3", o3)
    
    # Overall AQI is the maximum of all pollutant AQIs
    all_aqis = [
        aqi_pm25["aqi"],
        aqi_pm10["aqi"],
        aqi_no2["aqi"],
        aqi_so2["aqi"],
        aqi_co["aqi"],
        aqi_o3["aqi"]
    ]
    
    overall_aqi = max(all_aqis)
    dominant_pollutant_index = all_aqis.index(overall_aqi)
    pollutant_names = ["PM2.5", "PM10", "NO₂", "SO₂", "CO", "O₃"]
    dominant_pollutant = pollutant_names[dominant_pollutant_index]
    
    # Determine overall level
    if overall_aqi <= 50:
        level = AQILevel.GOOD
    elif overall_aqi <= 100:
        level = AQILevel.MODERATE
    elif overall_aqi <= 150:
        level = AQILevel.UNHEALTHY_SENSITIVE
    elif overall_aqi <= 200:
        level = AQILevel.UNHEALTHY
    elif overall_aqi <= 300:
        level = AQILevel.VERY_UNHEALTHY
    else:
        level = AQILevel.HAZARDOUS
    
    # Calculate European AQI
    european_aqi = calculate_european_aqi({
        "pm25": pm25,
        "pm10": pm10,
        "no2": no2,
        "o3": o3,
        "so2": so2
    })
    
    # Get health guidance
    health_guidance = get_health_guidance(overall_aqi, level)
    
    return {
        "status": "success",
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": times[current_index],
        "aqi": {
            "us_epa": {
                "value": overall_aqi,
                "level": level,
                "dominant_pollutant": dominant_pollutant
            },
            "european": european_aqi
        },
        "pollutants": {
            "pm2_5": {
                **aqi_pm25,
                "unit": "µg/m³",
                "health_impact": get_pollutant_health_impact("pm25", pm25)
            },
            "pm10": {
                **aqi_pm10,
                "unit": "µg/m³",
                "health_impact": get_pollutant_health_impact("pm10", pm10)
            },
            "nitrogen_dioxide": {
                **aqi_no2,
                "unit": "µg/m³",
                "health_impact": get_pollutant_health_impact("no2", no2)
            },
            "sulphur_dioxide": {
                **aqi_so2,
                "unit": "µg/m³",
                "health_impact": get_pollutant_health_impact("so2", so2)
            },
            "carbon_monoxide": {
                **aqi_co,
                "unit": "mg/m³",
                "concentration": round(co_mg, 2),
                "health_impact": get_pollutant_health_impact("co", co_mg)
            },
            "ozone": {
                **aqi_o3,
                "unit": "µg/m³",
                "health_impact": get_pollutant_health_impact("o3", o3)
            },
            "dust": {
                "concentration": round(dust, 2),
                "unit": "µg/m³"
            }
        },
        "health_guidance": health_guidance,
        "uv_index": round(uv_index, 1),
        "metadata": {
            "source": "Open-Meteo Air Quality API",
            "standards": ["US EPA AQI", "European EAQI"]
        }
    }


async def get_air_quality_forecast(latitude: float, longitude: float, days: int = 7) -> Dict[str, Any]:
    """
    Get air quality forecast
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
        days: Number of forecast days
        
    Returns:
        Daily air quality forecast
    """
    
    aq_data = await fetch_air_quality_data(latitude, longitude, days)
    
    if "error" in aq_data:
        return {
            "status": "unavailable",
            "message": "Air quality forecast temporarily unavailable"
        }
    
    hourly = aq_data.get("hourly", {})
    times = hourly.get("time", [])
    
    if not times:
        return {
            "status": "no_data",
            "message": "No air quality forecast available"
        }
    
    # Group by day
    daily_data = {}
    
    for i, time_str in enumerate(times):
        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        day_key = dt.date().isoformat()
        
        if day_key not in daily_data:
            daily_data[day_key] = {
                "pm25": [],
                "pm10": [],
                "no2": [],
                "so2": [],
                "co": [],
                "o3": [],
                "uv": []
            }
        
        daily_data[day_key]["pm25"].append(hourly.get("pm2_5", [0] * len(times))[i] or 0)
        daily_data[day_key]["pm10"].append(hourly.get("pm10", [0] * len(times))[i] or 0)
        daily_data[day_key]["no2"].append(hourly.get("nitrogen_dioxide", [0] * len(times))[i] or 0)
        daily_data[day_key]["so2"].append(hourly.get("sulphur_dioxide", [0] * len(times))[i] or 0)
        daily_data[day_key]["co"].append(hourly.get("carbon_monoxide", [0] * len(times))[i] or 0)
        daily_data[day_key]["o3"].append(hourly.get("ozone", [0] * len(times))[i] or 0)
        daily_data[day_key]["uv"].append(hourly.get("uv_index", [0] * len(times))[i] or 0)
    
    # Calculate daily aggregates
    forecast = []
    
    for day_key, day_values in sorted(daily_data.items()):
        # Use maximum values for AQI calculation (worst case)
        pm25_max = max(day_values["pm25"]) if day_values["pm25"] else 0
        pm10_max = max(day_values["pm10"]) if day_values["pm10"] else 0
        no2_max = max(day_values["no2"]) if day_values["no2"] else 0
        so2_max = max(day_values["so2"]) if day_values["so2"] else 0
        co_max = max(day_values["co"]) if day_values["co"] else 0
        o3_max = max(day_values["o3"]) if day_values["o3"] else 0
        uv_max = max(day_values["uv"]) if day_values["uv"] else 0
        
        co_max_mg = co_max / 1000
        
        # Calculate AQIs
        aqi_pm25 = calculate_us_epa_aqi("pm25", pm25_max)
        aqi_pm10 = calculate_us_epa_aqi("pm10", pm10_max)
        aqi_no2 = calculate_us_epa_aqi("no2", no2_max)
        aqi_so2 = calculate_us_epa_aqi("so2", so2_max)
        aqi_co = calculate_us_epa_aqi("co", co_max_mg)
        aqi_o3 = calculate_us_epa_aqi("o3", o3_max)
        
        overall_aqi = max([
            aqi_pm25["aqi"],
            aqi_pm10["aqi"],
            aqi_no2["aqi"],
            aqi_so2["aqi"],
            aqi_co["aqi"],
            aqi_o3["aqi"]
        ])
        
        if overall_aqi <= 50:
            level = AQILevel.GOOD
        elif overall_aqi <= 100:
            level = AQILevel.MODERATE
        elif overall_aqi <= 150:
            level = AQILevel.UNHEALTHY_SENSITIVE
        elif overall_aqi <= 200:
            level = AQILevel.UNHEALTHY
        elif overall_aqi <= 300:
            level = AQILevel.VERY_UNHEALTHY
        else:
            level = AQILevel.HAZARDOUS
        
        health_guidance = get_health_guidance(overall_aqi, level)
        
        forecast.append({
            "date": day_key,
            "aqi": {
                "value": overall_aqi,
                "level": level
            },
            "pollutants_max": {
                "pm2_5_µg_m3": round(pm25_max, 2),
                "pm10_µg_m3": round(pm10_max, 2),
                "no2_µg_m3": round(no2_max, 2),
                "so2_µg_m3": round(so2_max, 2),
                "co_mg_m3": round(co_max_mg, 2),
                "o3_µg_m3": round(o3_max, 2)
            },
            "max_uv_index": round(uv_max, 1),
            "health_guidance": health_guidance
        })
    
    return {
        "status": "success",
        "latitude": latitude,
        "longitude": longitude,
        "forecast_days": len(forecast),
        "daily_forecast": forecast,
        "metadata": {
            "source": "Open-Meteo Air Quality API",
            "note": "Daily values represent maximum (worst case) pollutant levels"
        }
    }
