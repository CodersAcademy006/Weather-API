"""
Weather V2 Routes - Phase 2 Enhanced Weather Endpoints

Provides hourly, daily, and historical weather data with CSV/JSON format support.
"""

import csv
import io
from datetime import datetime, timezone, date, timedelta
from typing import Optional, Literal

import requests
from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse

from config import settings
from logging_config import get_logger
from cache import get_cache, generate_weather_cache_key
from metrics import get_metrics
from schemas.weather import (
    WeatherUnits,
    ResponseFormat,
    HourlyWeatherResponse,
    DailyWeatherResponse,
    HistoricalWeatherResponse,
    HourlyDataPoint,
    DailyDataPoint
)

logger = get_logger(__name__)


def fetch_weatherapi_fallback(lat: float, lon: float, days: int = 1) -> dict:
    """Fetch weather data from WeatherAPI.com as fallback."""
    try:
        params = {
            "key": settings.WEATHERAPI_KEY,
            "q": f"{lat},{lon}",
            "days": min(days, 14),  # WeatherAPI supports up to 14 days
            "aqi": "yes",
            "alerts": "yes"
        }
        
        response = requests.get(
            settings.WEATHERAPI_URL,
            params=params,
            timeout=10
        )
        
        if response.status_code != 200:
            logger.error(f"WeatherAPI fallback failed with status {response.status_code}")
            return None
        
        logger.info(f"Successfully fetched data from WeatherAPI.com fallback for {lat},{lon}")
        return response.json()
        
    except Exception as e:
        logger.error(f"WeatherAPI fallback error: {e}")
        return None


def convert_weatherapi_to_hourly(weatherapi_data: dict, hours: int) -> dict:
    """Convert WeatherAPI.com response to our hourly format."""
    try:
        forecast = weatherapi_data.get("forecast", {}).get("forecastday", [])
        hourly_data = []
        
        for day in forecast:
            for hour in day.get("hour", []):
                if len(hourly_data) >= hours:
                    break
                hourly_data.append({
                    "time": hour.get("time"),
                    "temperature_2m": hour.get("temp_c"),
                    "apparent_temperature": hour.get("feelslike_c"),
                    "relative_humidity_2m": hour.get("humidity"),
                    "precipitation": hour.get("precip_mm"),
                    "precipitation_probability": hour.get("chance_of_rain", 0),
                    "wind_speed_10m": hour.get("wind_kph"),
                    "wind_direction_10m": hour.get("wind_degree"),
                    "cloud_cover": hour.get("cloud"),
                    "weather_code": hour.get("condition", {}).get("code"),
                    "uv_index": hour.get("uv"),
                    "visibility": hour.get("vis_km") * 1000 if hour.get("vis_km") else None,
                    "pressure_msl": hour.get("pressure_mb")
                })
            if len(hourly_data) >= hours:
                break
        
        return {
            "latitude": weatherapi_data.get("location", {}).get("lat"),
            "longitude": weatherapi_data.get("location", {}).get("lon"),
            "timezone": weatherapi_data.get("location", {}).get("tz_id", "UTC"),
            "hourly_raw": {
                "time": [h["time"] for h in hourly_data],
                "temperature_2m": [h["temperature_2m"] for h in hourly_data],
                "apparent_temperature": [h["apparent_temperature"] for h in hourly_data],
                "relative_humidity_2m": [h["relative_humidity_2m"] for h in hourly_data],
                "precipitation": [h["precipitation"] for h in hourly_data],
                "precipitation_probability": [h["precipitation_probability"] for h in hourly_data],
                "wind_speed_10m": [h["wind_speed_10m"] for h in hourly_data],
                "wind_direction_10m": [h["wind_direction_10m"] for h in hourly_data],
                "cloud_cover": [h["cloud_cover"] for h in hourly_data],
                "weather_code": [h["weather_code"] for h in hourly_data],
                "uv_index": [h["uv_index"] for h in hourly_data],
                "visibility": [h["visibility"] for h in hourly_data],
                "pressure_msl": [h["pressure_msl"] for h in hourly_data]
            }
        }
    except Exception as e:
        logger.error(f"Error converting WeatherAPI data to hourly format: {e}")
        return None


def convert_weatherapi_to_daily(weatherapi_data: dict, days: int) -> dict:
    """Convert WeatherAPI.com response to our daily format."""
    try:
        forecast = weatherapi_data.get("forecast", {}).get("forecastday", [])[:days]
        
        daily_data = []
        for day in forecast:
            daily_data.append({
                "date": day.get("date"),
                "temperature_2m_max": day.get("day", {}).get("maxtemp_c"),
                "temperature_2m_min": day.get("day", {}).get("mintemp_c"),
                "precipitation_sum": day.get("day", {}).get("totalprecip_mm"),
                "precipitation_probability_max": day.get("day", {}).get("daily_chance_of_rain", 0),
                "wind_speed_10m_max": day.get("day", {}).get("maxwind_kph"),
                "weather_code": day.get("day", {}).get("condition", {}).get("code"),
                "sunrise": day.get("astro", {}).get("sunrise"),
                "sunset": day.get("astro", {}).get("sunset"),
                "uv_index_max": day.get("day", {}).get("uv")
            })
        
        return {
            "latitude": weatherapi_data.get("location", {}).get("lat"),
            "longitude": weatherapi_data.get("location", {}).get("lon"),
            "timezone": weatherapi_data.get("location", {}).get("tz_id", "UTC"),
            "daily_raw": {
                "time": [d["date"] for d in daily_data],
                "temperature_2m_max": [d["temperature_2m_max"] for d in daily_data],
                "temperature_2m_min": [d["temperature_2m_min"] for d in daily_data],
                "precipitation_sum": [d["precipitation_sum"] for d in daily_data],
                "precipitation_probability_max": [d["precipitation_probability_max"] for d in daily_data],
                "wind_speed_10m_max": [d["wind_speed_10m_max"] for d in daily_data],
                "weather_code": [d["weather_code"] for d in daily_data],
                "sunrise": [d["sunrise"] for d in daily_data],
                "sunset": [d["sunset"] for d in daily_data],
                "uv_index_max": [d["uv_index_max"] for d in daily_data]
            }
        }
    except Exception as e:
        logger.error(f"Error converting WeatherAPI data to daily format: {e}")
        return None

router = APIRouter(
    prefix="/weather",
    tags=["Weather V2"],
    responses={
        400: {"description": "Bad Request"},
        429: {"description": "Rate Limited"},
        500: {"description": "Internal Server Error"},
        503: {"description": "External API Unavailable"}
    }
)


def normalize_coordinates(lat: float, lon: float) -> tuple:
    """Normalize coordinates to 2 decimal places."""
    return round(lat, 2), round(lon, 2)


def convert_temperature(temp_c: float, units: WeatherUnits) -> float:
    """Convert temperature to specified units."""
    if units == WeatherUnits.IMPERIAL:
        return round(temp_c * 9 / 5 + 32, 1)
    return round(temp_c, 1)


def convert_wind_speed(speed_kmh: float, units: WeatherUnits) -> float:
    """Convert wind speed to specified units."""
    if units == WeatherUnits.IMPERIAL:
        return round(speed_kmh * 0.621371, 1)  # to mph
    return round(speed_kmh / 3.6, 1)  # to m/s


@router.get(
    "/hourly",
    response_model=HourlyWeatherResponse,
    summary="Get hourly weather forecast",
    description="""
    Get hourly weather forecast for a location.
    
    **Parameters:**
    - `lat`: Latitude (-90 to 90)
    - `lon`: Longitude (-180 to 180)
    - `hours`: Forecast hours (24, 48, or 72)
    - `units`: metric (default) or imperial
    - `format`: json (default) or csv
    
    **Response:**
    Returns hourly forecast data including temperature, humidity, wind, precipitation probability.
    
    **Example:**
    ```
    curl "https://api.example.com/weather/hourly?lat=40.7128&lon=-74.006&hours=24"
    ```
    """
)
async def get_hourly_forecast(
    request: Request,
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    hours: Literal[24, 48, 72] = Query(24, description="Forecast hours"),
    units: WeatherUnits = Query(WeatherUnits.METRIC, description="Unit system"),
    format: ResponseFormat = Query(ResponseFormat.JSON, description="Response format")
):
    """Get hourly weather forecast."""
    metrics = get_metrics()
    metrics.increment("total_requests")
    metrics.increment("hourly_v2_requests")
    
    lat_norm, lon_norm = normalize_coordinates(lat, lon)
    cache_key = f"weather:hourly_v2:{lat_norm}:{lon_norm}:{hours}"
    
    cache = get_cache()
    cached = cache.get(cache_key)
    
    if cached:
        metrics.increment("cache_hits")
        logger.info(f"CACHE HIT for hourly v2 at {lat_norm}, {lon_norm}")
        data = cached
        source = "cache"
    else:
        metrics.increment("cache_misses")
        logger.info(f"CACHE MISS for hourly v2 at {lat_norm}, {lon_norm}")
        
        # Fetch from Open-Meteo with fallback to WeatherAPI
        data = None
        try:
            params = {
                "latitude": lat_norm,
                "longitude": lon_norm,
                "hourly": "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation_probability,precipitation,wind_speed_10m,wind_direction_10m,cloud_cover,weather_code,uv_index,visibility,pressure_msl",
                "forecast_days": (hours // 24) + 1,
                "timezone": "auto"
            }
            
            response = requests.get(
                settings.OPEN_METEO_API_URL,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                api_data = response.json()
                hourly = api_data.get("hourly", {})
                
                data = {
                    "latitude": api_data.get("latitude"),
                    "longitude": api_data.get("longitude"),
                    "timezone": api_data.get("timezone"),
                    "hourly_raw": hourly
                }
                source = "live"
                logger.info("Successfully fetched from Open-Meteo (primary)")
            else:
                raise Exception(f"Open-Meteo returned status {response.status_code}")
            
        except Exception as e:
            logger.warning(f"Primary API (Open-Meteo) failed: {e}")
            
            # Try fallback to WeatherAPI.com
            if settings.ENABLE_FALLBACK and not data:
                logger.info("Attempting fallback to WeatherAPI.com")
                metrics.increment("fallback_attempts")
                
                weatherapi_data = fetch_weatherapi_fallback(lat_norm, lon_norm, days=(hours // 24) + 1)
                if weatherapi_data:
                    data = convert_weatherapi_to_hourly(weatherapi_data, hours)
                    if data:
                        source = "fallback"
                        metrics.increment("fallback_successes")
                        logger.info("Successfully used WeatherAPI.com fallback")
                    else:
                        metrics.increment("fallback_failures")
                else:
                    metrics.increment("fallback_failures")
        
        # If both primary and fallback failed
        if not data:
            logger.error("Both primary and fallback APIs failed")
            raise HTTPException(
                status_code=503,
                detail="Weather service unavailable. Please try again later."
            )
        
        # Cache the result
        cache.set(cache_key, data, ttl=1800)  # 30 min cache
    
    # Process data
    hourly_raw = data.get("hourly_raw", {})
    times = hourly_raw.get("time", [])[:hours]
    
    hourly_data = []
    for i, time in enumerate(times):
        hourly_data.append(HourlyDataPoint(
            time=time,
            temperature=convert_temperature(hourly_raw.get("temperature_2m", [0])[i] or 0, units),
            feels_like=convert_temperature(hourly_raw.get("apparent_temperature", [0])[i] or 0, units),
            humidity=hourly_raw.get("relative_humidity_2m", [0])[i],
            precipitation=hourly_raw.get("precipitation", [0])[i],
            precipitation_probability=hourly_raw.get("precipitation_probability", [0])[i],
            wind_speed=convert_wind_speed(hourly_raw.get("wind_speed_10m", [0])[i] or 0, units),
            wind_direction=hourly_raw.get("wind_direction_10m", [0])[i],
            cloud_cover=hourly_raw.get("cloud_cover", [0])[i],
            weather_code=hourly_raw.get("weather_code", [0])[i],
            uv_index=hourly_raw.get("uv_index", [0])[i],
            visibility=hourly_raw.get("visibility", [0])[i],
            pressure=hourly_raw.get("pressure_msl", [0])[i]
        ))
    
    result = HourlyWeatherResponse(
        latitude=data.get("latitude", lat_norm),
        longitude=data.get("longitude", lon_norm),
        timezone=data.get("timezone", "UTC"),
        units=units,
        generated_at=datetime.now(timezone.utc).isoformat(),
        source=source,
        hourly=hourly_data
    )
    
    # Return CSV if requested
    if format == ResponseFormat.CSV:
        return _hourly_to_csv(result)
    
    return result


@router.get(
    "/daily",
    response_model=DailyWeatherResponse,
    summary="Get daily weather forecast",
    description="""
    Get daily weather forecast for a location.
    
    **Parameters:**
    - `lat`: Latitude (-90 to 90)
    - `lon`: Longitude (-180 to 180)
    - `days`: Forecast days (7 or 14)
    - `units`: metric (default) or imperial
    - `format`: json (default) or csv
    """
)
async def get_daily_forecast(
    request: Request,
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    days: Literal[7, 14] = Query(7, description="Forecast days"),
    units: WeatherUnits = Query(WeatherUnits.METRIC, description="Unit system"),
    format: ResponseFormat = Query(ResponseFormat.JSON, description="Response format")
):
    """Get daily weather forecast."""
    metrics = get_metrics()
    metrics.increment("total_requests")
    metrics.increment("daily_v2_requests")
    
    lat_norm, lon_norm = normalize_coordinates(lat, lon)
    cache_key = f"weather:daily_v2:{lat_norm}:{lon_norm}:{days}"
    
    cache = get_cache()
    cached = cache.get(cache_key)
    
    if cached:
        metrics.increment("cache_hits")
        logger.info(f"CACHE HIT for daily v2 at {lat_norm}, {lon_norm}")
        data = cached
        source = "cache"
    else:
        metrics.increment("cache_misses")
        logger.info(f"CACHE MISS for daily v2 at {lat_norm}, {lon_norm}")
        
        data = None
        try:
            params = {
                "latitude": lat_norm,
                "longitude": lon_norm,
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,sunrise,sunset,uv_index_max",
                "forecast_days": days,
                "timezone": "auto"
            }
            
            response = requests.get(
                settings.OPEN_METEO_API_URL,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                api_data = response.json()
                daily = api_data.get("daily", {})
                
                data = {
                    "latitude": api_data.get("latitude"),
                    "longitude": api_data.get("longitude"),
                    "timezone": api_data.get("timezone"),
                    "daily_raw": daily
                }
                source = "live"
                logger.info("Successfully fetched from Open-Meteo (primary)")
            else:
                raise Exception(f"Open-Meteo returned status {response.status_code}")
            
        except Exception as e:
            logger.warning(f"Primary API (Open-Meteo) failed: {e}")
            
            # Try fallback to WeatherAPI.com
            if settings.ENABLE_FALLBACK and not data:
                logger.info("Attempting fallback to WeatherAPI.com")
                metrics.increment("fallback_attempts")
                
                weatherapi_data = fetch_weatherapi_fallback(lat_norm, lon_norm, days=days)
                if weatherapi_data:
                    data = convert_weatherapi_to_daily(weatherapi_data, days)
                    if data:
                        source = "fallback"
                        metrics.increment("fallback_successes")
                        logger.info("Successfully used WeatherAPI.com fallback")
                    else:
                        metrics.increment("fallback_failures")
                else:
                    metrics.increment("fallback_failures")
        
        # If both primary and fallback failed
        if not data:
            logger.error("Both primary and fallback APIs failed")
            raise HTTPException(
                status_code=503,
                detail="Weather service unavailable. Please try again later."
            )
        
        # Cache the result
        cache.set(cache_key, data, ttl=3600)  # 1 hour cache
    
    # Process data
    daily_raw = data.get("daily_raw", {})
    dates = daily_raw.get("time", [])
    
    daily_data = []
    for i, date_str in enumerate(dates):
        daily_data.append(DailyDataPoint(
            date=date_str,
            temperature_max=convert_temperature(daily_raw.get("temperature_2m_max", [0])[i] or 0, units),
            temperature_min=convert_temperature(daily_raw.get("temperature_2m_min", [0])[i] or 0, units),
            precipitation_sum=daily_raw.get("precipitation_sum", [0])[i],
            precipitation_probability_max=daily_raw.get("precipitation_probability_max", [0])[i],
            wind_speed_max=convert_wind_speed(daily_raw.get("wind_speed_10m_max", [0])[i] or 0, units),
            weather_code=daily_raw.get("weather_code", [0])[i],
            sunrise=daily_raw.get("sunrise", [""])[i],
            sunset=daily_raw.get("sunset", [""])[i],
            uv_index_max=daily_raw.get("uv_index_max", [0])[i]
        ))
    
    result = DailyWeatherResponse(
        latitude=data.get("latitude", lat_norm),
        longitude=data.get("longitude", lon_norm),
        timezone=data.get("timezone", "UTC"),
        units=units,
        generated_at=datetime.now(timezone.utc).isoformat(),
        source=source,
        daily=daily_data
    )
    
    if format == ResponseFormat.CSV:
        return _daily_to_csv(result)
    
    return result


@router.get(
    "/historical",
    response_model=HistoricalWeatherResponse,
    summary="Get historical weather data",
    description="""
    Get historical weather data for a location.
    
    **Parameters:**
    - `lat`: Latitude (-90 to 90)
    - `lon`: Longitude (-180 to 180)
    - `start`: Start date (YYYY-MM-DD)
    - `end`: End date (YYYY-MM-DD)
    - `units`: metric (default) or imperial
    - `format`: json (default) or csv
    
    **Constraints:**
    - Date range cannot exceed 365 days
    - End date must be after start date
    """
)
async def get_historical_weather(
    request: Request,
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    start: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: date = Query(..., description="End date (YYYY-MM-DD)"),
    units: WeatherUnits = Query(WeatherUnits.METRIC, description="Unit system"),
    format: ResponseFormat = Query(ResponseFormat.JSON, description="Response format")
):
    """Get historical weather data."""
    # Validate date range
    if end < start:
        raise HTTPException(
            status_code=400,
            detail="End date must be after start date"
        )
    
    if (end - start).days > 365:
        raise HTTPException(
            status_code=400,
            detail="Date range cannot exceed 365 days"
        )
    
    metrics = get_metrics()
    metrics.increment("total_requests")
    metrics.increment("historical_requests")
    
    lat_norm, lon_norm = normalize_coordinates(lat, lon)
    cache_key = f"weather:historical:{lat_norm}:{lon_norm}:{start}:{end}"
    
    cache = get_cache()
    cached = cache.get(cache_key)
    
    if cached:
        metrics.increment("cache_hits")
        logger.info(f"CACHE HIT for historical at {lat_norm}, {lon_norm}")
        data = cached
        source = "cache"
    else:
        metrics.increment("cache_misses")
        logger.info(f"CACHE MISS for historical at {lat_norm}, {lon_norm}")
        
        try:
            params = {
                "latitude": lat_norm,
                "longitude": lon_norm,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,sunrise,sunset",
                "timezone": "auto"
            }
            
            response = requests.get(
                settings.OPEN_METEO_HISTORICAL_URL,
                params=params,
                timeout=30
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=503,
                    detail="Historical weather service temporarily unavailable"
                )
            
            api_data = response.json()
            daily = api_data.get("daily", {})
            
            data = {
                "latitude": api_data.get("latitude"),
                "longitude": api_data.get("longitude"),
                "timezone": api_data.get("timezone"),
                "daily_raw": daily
            }
            
            cache.set(cache_key, data, ttl=86400)  # 24 hour cache for historical
            source = "live"
            
        except requests.exceptions.Timeout:
            raise HTTPException(
                status_code=503,
                detail="Historical weather service timeout. Please try again."
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise HTTPException(
                status_code=503,
                detail="Historical weather service unavailable"
            )
    
    # Process data
    daily_raw = data.get("daily_raw", {})
    dates = daily_raw.get("time", [])
    
    daily_data = []
    for i, date_str in enumerate(dates):
        daily_data.append(DailyDataPoint(
            date=date_str,
            temperature_max=convert_temperature(daily_raw.get("temperature_2m_max", [0])[i] or 0, units),
            temperature_min=convert_temperature(daily_raw.get("temperature_2m_min", [0])[i] or 0, units),
            precipitation_sum=daily_raw.get("precipitation_sum", [0])[i],
            wind_speed_max=convert_wind_speed(daily_raw.get("wind_speed_10m_max", [0])[i] or 0, units),
            weather_code=daily_raw.get("weather_code", [0])[i],
            sunrise=daily_raw.get("sunrise", [""])[i] if daily_raw.get("sunrise") else None,
            sunset=daily_raw.get("sunset", [""])[i] if daily_raw.get("sunset") else None
        ))
    
    result = HistoricalWeatherResponse(
        latitude=data.get("latitude", lat_norm),
        longitude=data.get("longitude", lon_norm),
        timezone=data.get("timezone", "UTC"),
        units=units,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        generated_at=datetime.now(timezone.utc).isoformat(),
        source=source,
        daily=daily_data
    )
    
    if format == ResponseFormat.CSV:
        return _historical_to_csv(result)
    
    return result


def _hourly_to_csv(data: HourlyWeatherResponse) -> StreamingResponse:
    """Convert hourly response to CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "time", "temperature", "feels_like", "humidity", "precipitation",
        "precipitation_probability", "wind_speed", "wind_direction",
        "cloud_cover", "weather_code", "uv_index", "pressure"
    ])
    
    # Data
    for h in data.hourly:
        writer.writerow([
            h.time, h.temperature, h.feels_like, h.humidity, h.precipitation,
            h.precipitation_probability, h.wind_speed, h.wind_direction,
            h.cloud_cover, h.weather_code, h.uv_index, h.pressure
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=hourly_forecast_{data.latitude}_{data.longitude}.csv"}
    )


def _daily_to_csv(data: DailyWeatherResponse) -> StreamingResponse:
    """Convert daily response to CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        "date", "temperature_max", "temperature_min", "precipitation_sum",
        "precipitation_probability_max", "wind_speed_max", "weather_code",
        "sunrise", "sunset", "uv_index_max"
    ])
    
    for d in data.daily:
        writer.writerow([
            d.date, d.temperature_max, d.temperature_min, d.precipitation_sum,
            d.precipitation_probability_max, d.wind_speed_max, d.weather_code,
            d.sunrise, d.sunset, d.uv_index_max
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=daily_forecast_{data.latitude}_{data.longitude}.csv"}
    )


def _historical_to_csv(data: HistoricalWeatherResponse) -> StreamingResponse:
    """Convert historical response to CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        "date", "temperature_max", "temperature_min", "precipitation_sum",
        "wind_speed_max", "weather_code", "sunrise", "sunset"
    ])
    
    for d in data.daily:
        writer.writerow([
            d.date, d.temperature_max, d.temperature_min, d.precipitation_sum,
            d.wind_speed_max, d.weather_code, d.sunrise, d.sunset
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=historical_{data.latitude}_{data.longitude}_{data.start_date}_{data.end_date}.csv"}
    )
