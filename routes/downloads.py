"""
Download Routes - PDF and Excel Report Downloads

Provides endpoints for downloading weather reports in PDF and Excel formats.
"""

from datetime import datetime, timezone
from typing import Literal

import requests
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse

from config import settings
from logging_config import get_logger
from cache import get_cache
from metrics import get_metrics
from modules.reports import PDFReportGenerator, ExcelReportGenerator

logger = get_logger(__name__)

router = APIRouter(
    prefix="/weather/download",
    tags=["Downloads"],
    responses={
        400: {"description": "Bad Request"},
        429: {"description": "Rate Limited"},
        503: {"description": "Service Unavailable"}
    }
)


def _fetch_weather_data(lat: float, lon: float, report_range: str, days: int) -> dict:
    """Fetch weather data for report generation."""
    lat_norm = round(lat, 2)
    lon_norm = round(lon, 2)
    
    try:
        if report_range == "hourly":
            params = {
                "latitude": lat_norm,
                "longitude": lon_norm,
                "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,wind_speed_10m,weather_code",
                "forecast_days": min(days, 3),
                "timezone": "auto"
            }
            
            response = requests.get(
                settings.OPEN_METEO_API_URL,
                params=params,
                timeout=15
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            hourly = data.get("hourly", {})
            
            hourly_list = []
            times = hourly.get("time", [])
            for i, time in enumerate(times):
                hourly_list.append({
                    "time": time,
                    "temperature": hourly.get("temperature_2m", [0])[i],
                    "humidity": hourly.get("relative_humidity_2m", [0])[i],
                    "precipitation_probability": hourly.get("precipitation_probability", [0])[i],
                    "wind_speed": hourly.get("wind_speed_10m", [0])[i],
                    "weather_code": hourly.get("weather_code", [0])[i]
                })
            
            return {
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "timezone": data.get("timezone"),
                "hourly": hourly_list
            }
        
        else:  # daily
            params = {
                "latitude": lat_norm,
                "longitude": lon_norm,
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,sunrise,sunset",
                "forecast_days": min(days, 14),
                "timezone": "auto"
            }
            
            response = requests.get(
                settings.OPEN_METEO_API_URL,
                params=params,
                timeout=15
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            daily = data.get("daily", {})
            
            daily_list = []
            dates = daily.get("time", [])
            for i, date in enumerate(dates):
                daily_list.append({
                    "date": date,
                    "temperature_max": daily.get("temperature_2m_max", [0])[i],
                    "temperature_min": daily.get("temperature_2m_min", [0])[i],
                    "precipitation_sum": daily.get("precipitation_sum", [0])[i],
                    "precipitation_probability_max": daily.get("precipitation_probability_max", [0])[i],
                    "weather_code": daily.get("weather_code", [0])[i],
                    "sunrise": daily.get("sunrise", [""])[i],
                    "sunset": daily.get("sunset", [""])[i]
                })
            
            return {
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "timezone": data.get("timezone"),
                "daily": daily_list
            }
    
    except Exception as e:
        logger.error(f"Failed to fetch weather data for report: {e}")
        return None


@router.get(
    "",
    summary="Download weather report",
    description="""
    Download weather data as PDF or Excel report.
    
    **Parameters:**
    - `lat`: Latitude (-90 to 90)
    - `lon`: Longitude (-180 to 180)
    - `type`: Report format (pdf or excel)
    - `range`: Data range (hourly or daily)
    - `days`: Number of days (1-14)
    
    **Example:**
    ```
    curl "https://api.example.com/weather/download?lat=40.7128&lon=-74.006&type=pdf&range=daily&days=7" -o report.pdf
    ```
    
    **PDF Report includes:**
    - Formatted weather tables
    - Simple temperature charts
    - Location metadata
    
    **Excel Report includes:**
    - Weather data sheet with styling
    - Metadata sheet
    - Column headers and formatting
    """
)
async def download_report(
    request: Request,
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    type: Literal["pdf", "excel"] = Query("pdf", description="Report format"),
    range: Literal["hourly", "daily"] = Query("daily", description="Data range"),
    days: int = Query(7, ge=1, le=14, description="Number of days")
):
    """Download weather report as PDF or Excel."""
    metrics = get_metrics()
    metrics.increment("total_requests")
    metrics.increment("download_requests")
    
    lat_norm = round(lat, 2)
    lon_norm = round(lon, 2)
    
    # Check cache for generated report
    cache_key = f"report:{type}:{range}:{lat_norm}:{lon_norm}:{days}"
    cache = get_cache()
    
    cached = cache.get(cache_key)
    if cached:
        metrics.increment("cache_hits")
        logger.info(f"REPORT CACHE HIT for {lat_norm}, {lon_norm}")
        report_bytes = cached["data"]
        content_type = cached["content_type"]
        filename = cached["filename"]
    else:
        metrics.increment("cache_misses")
        logger.info(f"REPORT CACHE MISS for {lat_norm}, {lon_norm}")
        
        # Fetch weather data
        weather_data = _fetch_weather_data(lat_norm, lon_norm, range, days)
        
        if not weather_data:
            raise HTTPException(
                status_code=503,
                detail="Failed to fetch weather data for report"
            )
        
        location = f"Location ({lat_norm}, {lon_norm})"
        
        # Generate report
        if type == "pdf":
            generator = PDFReportGenerator()
            report_bytes = generator.generate(location, weather_data, range)
            content_type = "application/pdf"
            filename = f"weather_report_{lat_norm}_{lon_norm}_{range}.pdf"
        else:
            generator = ExcelReportGenerator()
            report_bytes = generator.generate(location, weather_data, range)
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"weather_report_{lat_norm}_{lon_norm}_{range}.xlsx"
        
        # Cache the generated report
        cache.set(cache_key, {
            "data": report_bytes,
            "content_type": content_type,
            "filename": filename
        }, ttl=settings.REPORTS_CACHE_TTL_SECONDS)
    
    return Response(
        content=report_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
