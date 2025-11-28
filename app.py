"""
IntelliWeather API - Production-Grade Weather Service

A modern, feature-rich weather API built with FastAPI featuring:
- Real-time weather data from Open-Meteo
- In-memory caching with TTL
- CSV-based data storage
- Session-based authentication
- Rate limiting
- Health checks and metrics

Phase 2 Features:
- Hourly, daily, and historical weather endpoints
- Geocoding and reverse geocoding
- Weather alerts
- PDF/Excel report downloads
- ML-based temperature predictions
- Multi-language support
- API key management
- Admin dashboard
"""

import requests
import json
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta, timezone

# Import configuration and modules
from config import settings
from logging_config import setup_logging, get_logger
from cache import get_cache, generate_weather_cache_key, init_cache
from storage import get_storage, init_storage, CachedWeather
from session_middleware import SessionMiddleware, set_session_middleware, optional_auth
from middleware.rate_limiter import RateLimiterMiddleware
from routes.auth import router as auth_router
from metrics import router as metrics_router, get_metrics

# Phase 2 routers
from routes.weather_v2 import router as weather_v2_router
from routes.geocode import router as geocode_router
from routes.alerts import router as alerts_router
from routes.downloads import router as downloads_router
from routes.apikeys import router as apikeys_router
from routes.predict import router as predict_router
from routes.admin import router as admin_router
from routes.i18n import router as i18n_router
from routes.growth import router as growth_router

# Initialize logging
logger = get_logger(__name__)


# ==================== APPLICATION LIFECYCLE ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Initialize components
    init_storage()
    init_cache()
    
    # Initialize Sentry if configured
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk
            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                traces_sample_rate=0.1,
            )
            logger.info("Sentry initialized")
        except ImportError:
            logger.warning("Sentry SDK not installed, skipping initialization")
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    cache = get_cache()
    if cache:
        cache.shutdown()
    logger.info("Application shutdown complete")


# ==================== APPLICATION SETUP ====================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
# IntelliWeather API

Production-grade weather API with caching, authentication, and rate limiting.

## Features

### Phase 1
- Real-time weather data
- In-memory caching
- Session-based authentication
- Rate limiting
- Health & metrics

### Phase 2
- **Weather V2**: Hourly, daily, and historical endpoints with CSV export
- **Geocoding**: Location search and reverse geocoding
- **Alerts**: Weather alerts and warnings
- **Downloads**: PDF and Excel weather reports
- **ML Prediction**: Next-day temperature prediction
- **i18n**: Multi-language support (EN, HI, UR, AR, ES)
- **API Keys**: Per-key rate limiting
- **Admin Dashboard**: Analytics and monitoring

## Authentication

Use session cookies or API keys for authentication.
""",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Weather", "description": "Current weather and basic forecasts"},
        {"name": "Weather V2", "description": "Enhanced weather endpoints with CSV support"},
        {"name": "Geocoding", "description": "Location search and reverse geocoding"},
        {"name": "Weather Alerts", "description": "Active alerts and warnings"},
        {"name": "Downloads", "description": "PDF and Excel report downloads"},
        {"name": "ML Prediction", "description": "Machine learning predictions"},
        {"name": "Internationalization", "description": "Multi-language support"},
        {"name": "API Keys", "description": "API key management"},
        {"name": "Auth", "description": "Authentication endpoints"},
        {"name": "Admin", "description": "Admin dashboard and analytics"},
        {"name": "Health", "description": "Health checks and metrics"},
    ]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiter middleware
app.add_middleware(RateLimiterMiddleware)

# Add session middleware
session_middleware = SessionMiddleware(app)
set_session_middleware(session_middleware)

# Include Phase 1 routers
app.include_router(auth_router)
app.include_router(metrics_router)

# Include Phase 2 routers (conditionally based on feature flags)
if settings.FEATURE_WEATHER_V2:
    app.include_router(weather_v2_router)
    logger.info("Weather V2 routes enabled")

if settings.FEATURE_GEOCODING:
    app.include_router(geocode_router)
    logger.info("Geocoding routes enabled")

if settings.FEATURE_ALERTS:
    app.include_router(alerts_router)
    logger.info("Alerts routes enabled")

if settings.FEATURE_DOWNLOADS:
    app.include_router(downloads_router)
    logger.info("Downloads routes enabled")

if settings.FEATURE_API_KEYS:
    app.include_router(apikeys_router)
    logger.info("API Keys routes enabled")

if settings.FEATURE_ML_PREDICTION:
    app.include_router(predict_router)
    logger.info("ML Prediction routes enabled")

if settings.FEATURE_ADMIN_DASHBOARD:
    app.include_router(admin_router)
    logger.info("Admin dashboard routes enabled")

if settings.FEATURE_I18N:
    app.include_router(i18n_router)
    logger.info("i18n routes enabled")

# Phase 3: Growth features
if settings.FEATURE_ANALYTICS or settings.FEATURE_REFERRALS or settings.FEATURE_SHAREABLE_LINKS:
    app.include_router(growth_router)
    logger.info("Growth routes enabled")


# ==================== DATABASE CONNECTION (Legacy Support) ====================

def get_db_connection():
    """Get database connection if configured."""
    if settings.DB_CONNECTION_STRING:
        try:
            import psycopg2
            return psycopg2.connect(settings.DB_CONNECTION_STRING)
        except Exception as e:
            logger.warning(f"Database connection failed: {e}")
    return None

# ==================== HELPER FUNCTIONS ====================

def normalize_coordinates(lat: float, lon: float) -> tuple:
    """Normalize coordinates to 2 decimal places for caching."""
    return round(lat, 2), round(lon, 2)


# --- CURRENT WEATHER ---
def get_weather_from_db(lat: float, lon: float) -> Optional[tuple]:
    """Get weather from database (legacy support)."""
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        query = "SELECT * FROM weather_readings WHERE latitude = %s AND longitude = %s AND timestamp >= %s ORDER BY timestamp DESC LIMIT 1;"
        cursor.execute(query, (lat, lon, one_hour_ago))
        result = cursor.fetchone()
        return result
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        return None
    finally:
        conn.close()


def save_weather_to_db(data_rows: list) -> None:
    """Save weather to database (legacy support)."""
    conn = get_db_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        insert_query = "INSERT INTO weather_readings (location_name, latitude, longitude, timestamp, temperature_c, humidity_pct, pressure_hpa, wind_speed_mps, precip_mm, weather_code, apparent_temperature, uv_index, is_day) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (location_name, timestamp) DO NOTHING;"
        for row in data_rows:
            values = (row['location_name'], row['latitude'], row['longitude'], row['timestamp'], row['temperature_c'], row['humidity_pct'], row['pressure_hpa'], row['wind_speed_mps'], row['precip_mm'], row['weather_code'], row['apparent_temperature'], row['uv_index'], row['is_day'])
            cursor.execute(insert_query, values)
        conn.commit()
    except Exception as e:
        logger.error(f"Database save failed: {e}")
    finally:
        conn.close()


def fetch_live_weather(lat: float, lon: float) -> Optional[dict]:
    """Fetch live weather from Open-Meteo API."""
    try:
        api_url = settings.OPEN_METEO_API_URL
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,apparent_temperature,precipitation,weather_code,relative_humidity_2m,wind_speed_10m,uv_index,pressure_msl,is_day",
            "timezone": "auto"
        }
        response = requests.get(api_url, params=params, timeout=10)
        if response.status_code != 200:
            logger.error(f"Open-Meteo API error: {response.status_code}")
            return None
        raw = response.json()['current']
        return {
            "location_name": f"Lat_{lat}_Lon_{lon}",
            "latitude": lat,
            "longitude": lon,
            "timestamp": datetime.fromisoformat(raw['time']),
            "temperature_c": raw['temperature_2m'],
            "humidity_pct": raw['relative_humidity_2m'],
            "pressure_hpa": raw['pressure_msl'],
            "wind_speed_mps": round(raw['wind_speed_10m'] / 3.6, 2),
            "precip_mm": raw['precipitation'],
            "weather_code": raw['weather_code'],
            "apparent_temperature": raw['apparent_temperature'],
            "uv_index": raw['uv_index'],
            "is_day": raw['is_day']
        }
    except Exception as e:
        logger.error(f"Failed to fetch live weather: {e}")
        return None


# --- HOURLY FORECAST ---
def get_hourly_forecast_from_db(lat: float, lon: float) -> Optional[list]:
    """Get hourly forecast from database (legacy support)."""
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        six_hours_ago = datetime.now(timezone.utc) - timedelta(hours=6)
        query = "SELECT forecast_time, temperature_c, precipitation_prob, wind_speed_mps, cloud_cover, weather_code FROM hourly_forecasts WHERE latitude = %s AND longitude = %s AND created_at >= %s ORDER BY forecast_time ASC LIMIT 24;"
        cursor.execute(query, (lat, lon, six_hours_ago))
        results = cursor.fetchall()
        return results if results else None
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        return None
    finally:
        conn.close()


def save_hourly_forecast_to_db(lat: float, lon: float, forecast_data: list) -> None:
    """Save hourly forecast to database (legacy support)."""
    conn = get_db_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        query = "INSERT INTO hourly_forecasts (latitude, longitude, forecast_time, temperature_c, precipitation_prob, wind_speed_mps, cloud_cover, weather_code) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (latitude, longitude, forecast_time) DO UPDATE SET temperature_c = EXCLUDED.temperature_c, precipitation_prob = EXCLUDED.precipitation_prob, wind_speed_mps = EXCLUDED.wind_speed_mps, cloud_cover = EXCLUDED.cloud_cover, weather_code = EXCLUDED.weather_code, created_at = NOW();"
        for hour in forecast_data:
            values = (lat, lon, hour['time'], hour['temp'], hour['precip_prob'], hour['wind'], hour['cloud_cover'], hour['weather_code'])
            cursor.execute(query, values)
        conn.commit()
    except Exception as e:
        logger.error(f"Database save failed: {e}")
    finally:
        conn.close()


def fetch_hourly_forecast(lat: float, lon: float) -> Optional[list]:
    """Fetch hourly forecast from Open-Meteo API."""
    try:
        api_url = settings.OPEN_METEO_API_URL
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,precipitation_probability,wind_speed_10m,cloud_cover,weather_code",
            "forecast_days": 1,
            "timezone": "auto"
        }
        response = requests.get(api_url, params=params, timeout=10)
        if response.status_code != 200:
            return None
        raw = response.json()['hourly']
        return [
            {
                "time": raw['time'][i],
                "temp": raw['temperature_2m'][i],
                "precip_prob": raw['precipitation_probability'][i],
                "wind": round(raw['wind_speed_10m'][i] / 3.6, 2),
                "cloud_cover": raw['cloud_cover'][i],
                "weather_code": raw['weather_code'][i]
            }
            for i in range(len(raw['time']))
        ]
    except Exception as e:
        logger.error(f"Failed to fetch hourly forecast: {e}")
        return None


# --- DAILY FORECAST ---
def get_forecast_from_db(lat: float, lon: float) -> Optional[list]:
    """Get daily forecast from database (legacy support)."""
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        six_hours_ago = datetime.now(timezone.utc) - timedelta(hours=6)
        query = "SELECT forecast_date, max_temp_c, min_temp_c, weather_code, sunrise, sunset, precipitation_sum, precipitation_probability_max FROM daily_forecasts WHERE latitude = %s AND longitude = %s AND created_at >= %s ORDER BY forecast_date ASC;"
        cursor.execute(query, (lat, lon, six_hours_ago))
        results = cursor.fetchall()
        return results if results else None
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        return None
    finally:
        conn.close()


def save_forecast_to_db(lat: float, lon: float, forecast_data: list) -> None:
    """Save daily forecast to database (legacy support)."""
    conn = get_db_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        query = "INSERT INTO daily_forecasts (latitude, longitude, forecast_date, max_temp_c, min_temp_c, weather_code, sunrise, sunset, precipitation_sum, precipitation_probability_max) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (latitude, longitude, forecast_date) DO UPDATE SET max_temp_c = EXCLUDED.max_temp_c, min_temp_c = EXCLUDED.min_temp_c, weather_code = EXCLUDED.weather_code, sunrise = EXCLUDED.sunrise, sunset = EXCLUDED.sunset, precipitation_sum = EXCLUDED.precipitation_sum, precipitation_probability_max = EXCLUDED.precipitation_probability_max, created_at = NOW();"
        for day in forecast_data:
            values = (lat, lon, day['date'], day['max_temp'], day['min_temp'], day['weather_code'], day['sunrise'], day['sunset'], day['precipitation_sum'], day['precipitation_probability_max'])
            cursor.execute(query, values)
        conn.commit()
    except Exception as e:
        logger.error(f"Database save failed: {e}")
    finally:
        conn.close()


def fetch_daily_forecast(lat: float, lon: float) -> Optional[list]:
    """Fetch daily forecast from Open-Meteo API."""
    try:
        api_url = settings.OPEN_METEO_API_URL
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,precipitation_sum,precipitation_probability_max",
            "forecast_days": 7,
            "timezone": "auto"
        }
        response = requests.get(api_url, params=params, timeout=10)
        if response.status_code != 200:
            return None
        raw = response.json()['daily']
        return [
            {
                "date": raw['time'][i],
                "max_temp": raw['temperature_2m_max'][i],
                "min_temp": raw['temperature_2m_min'][i],
                "weather_code": raw['weather_code'][i],
                "sunrise": raw['sunrise'][i],
                "sunset": raw['sunset'][i],
                "precipitation_sum": raw['precipitation_sum'][i],
                "precipitation_probability_max": raw['precipitation_probability_max'][i]
            }
            for i in range(len(raw['time']))
        ]
    except Exception as e:
        logger.error(f"Failed to fetch daily forecast: {e}")
        return None


# --- AQI & ALERTS ---
def fetch_aqi_and_alerts(lat: float, lon: float) -> dict:
    """Fetch AQI and alerts from Open-Meteo API."""
    try:
        air_quality_api_url = settings.OPEN_METEO_AIR_QUALITY_URL
        forecast_api_url = settings.OPEN_METEO_API_URL
        aqi_params = {"latitude": lat, "longitude": lon, "hourly": "us_aqi,pm2_5,carbon_monoxide,ozone", "timezone": "auto"}
        alerts_params = {"latitude": lat, "longitude": lon, "daily": "weather_code", "forecast_days": 1}

        aqi_response = requests.get(air_quality_api_url, params=aqi_params, timeout=10)
        alerts_response = requests.get(forecast_api_url, params=alerts_params, timeout=10)
        
        aqi_data = aqi_response.json() if aqi_response.status_code == 200 else None
        alerts = alerts_response.json().get("daily", {}).get("alerts", []) if alerts_response.status_code == 200 else []
        
        return {"aqi": aqi_data, "alerts": alerts}
    except Exception as e:
        logger.error(f"Failed to fetch AQI/alerts: {e}")
        return {"aqi": None, "alerts": []}

# ==================== API ENDPOINTS ====================

@app.get("/weather")
def get_weather(request: Request, lat: float, lon: float):
    """
    Get current weather for a location.
    
    Uses multi-tier caching:
    1. In-memory cache (fastest)
    2. Database cache (if configured)
    3. Live API call (fallback)
    """
    metrics = get_metrics()
    metrics.increment("total_requests")
    metrics.increment("weather_requests")
    
    # Normalize coordinates
    lat_norm, lon_norm = normalize_coordinates(lat, lon)
    cache_key = generate_weather_cache_key(lat_norm, lon_norm, "current")
    
    # Check in-memory cache first
    cache = get_cache()
    cached_data = cache.get(cache_key)
    
    if cached_data:
        metrics.increment("cache_hits")
        logger.info(f"CACHE HIT for current weather at {lat_norm}, {lon_norm}")
        return {"source": "cache", **cached_data}
    
    metrics.increment("cache_misses")
    
    # Try database cache (legacy)
    db_cached = get_weather_from_db(lat_norm, lon_norm)
    if db_cached and len(db_cached) >= 14:
        logger.info(f"DB CACHE HIT for current weather at {lat_norm}, {lon_norm}")
        result = {
            "source": "db_cache",
            "timestamp": db_cached[4],
            "temperature_c": db_cached[5],
            "humidity_pct": db_cached[6],
            "pressure_hpa": db_cached[7],
            "wind_speed_mps": db_cached[8],
            "precip_mm": db_cached[9],
            "weather_code": db_cached[10],
            "apparent_temperature": db_cached[11],
            "uv_index": db_cached[12],
            "is_day": db_cached[13]
        }
        # Store in memory cache
        cache.set(cache_key, result)
        return result
    
    # Fetch live data
    logger.info(f"CACHE MISS for current weather at {lat_norm}, {lon_norm}. Fetching live data...")
    live = fetch_live_weather(lat_norm, lon_norm)
    
    if not live:
        raise HTTPException(status_code=500, detail="Could not retrieve live weather data.")
    
    # Prepare result
    result = {
        "temperature_c": live["temperature_c"],
        "humidity_pct": live["humidity_pct"],
        "pressure_hpa": live["pressure_hpa"],
        "wind_speed_mps": live["wind_speed_mps"],
        "precip_mm": live["precip_mm"],
        "weather_code": live["weather_code"],
        "apparent_temperature": live["apparent_temperature"],
        "uv_index": live["uv_index"],
        "is_day": live["is_day"]
    }
    
    # Cache in memory
    cache.set(cache_key, result)
    
    # Save to database (legacy)
    save_weather_to_db([live])
    
    # Save to CSV storage for popular locations
    try:
        storage = get_storage()
        storage.save_cached_weather(CachedWeather.create(
            lat=lat_norm,
            lon=lon_norm,
            location_name=live["location_name"],
            data_type="current",
            data=json.dumps(result)
        ))
    except Exception as e:
        logger.warning(f"Failed to save to CSV storage: {e}")
    
    return {"source": "live", **result}


@app.get("/hourly")
def get_hourly_forecast_endpoint(request: Request, lat: float, lon: float):
    """
    Get hourly forecast for a location.
    """
    metrics = get_metrics()
    metrics.increment("total_requests")
    metrics.increment("hourly_requests")
    
    lat_norm, lon_norm = normalize_coordinates(lat, lon)
    cache_key = generate_weather_cache_key(lat_norm, lon_norm, "hourly")
    
    # Check memory cache
    cache = get_cache()
    cached_data = cache.get(cache_key)
    
    if cached_data:
        metrics.increment("cache_hits")
        logger.info(f"CACHE HIT for hourly forecast at {lat_norm}, {lon_norm}")
        return cached_data
    
    metrics.increment("cache_misses")
    
    # Try database
    db_cached = get_hourly_forecast_from_db(lat_norm, lon_norm)
    if db_cached and len(db_cached) >= 24:
        logger.info(f"DB CACHE HIT for hourly forecast at {lat_norm}, {lon_norm}")
        result = [{"time": r[0], "temp": r[1], "precip_prob": r[2], "wind": r[3], "cloud_cover": r[4], "weather_code": r[5]} for r in db_cached]
        cache.set(cache_key, result)
        return result
    
    # Fetch live
    logger.info(f"CACHE MISS for hourly forecast at {lat_norm}, {lon_norm}. Fetching live data...")
    live = fetch_hourly_forecast(lat_norm, lon_norm)
    
    if not live:
        raise HTTPException(status_code=500, detail="Could not retrieve hourly forecast.")
    
    # Cache and save
    cache.set(cache_key, live)
    save_hourly_forecast_to_db(lat_norm, lon_norm, live)
    
    return live


@app.get("/forecast")
def get_daily_forecast_endpoint(request: Request, lat: float, lon: float):
    """
    Get 7-day forecast for a location.
    """
    metrics = get_metrics()
    metrics.increment("total_requests")
    metrics.increment("forecast_requests")
    
    lat_norm, lon_norm = normalize_coordinates(lat, lon)
    cache_key = generate_weather_cache_key(lat_norm, lon_norm, "daily")
    
    # Check memory cache
    cache = get_cache()
    cached_data = cache.get(cache_key)
    
    if cached_data:
        metrics.increment("cache_hits")
        logger.info(f"CACHE HIT for daily forecast at {lat_norm}, {lon_norm}")
        return cached_data
    
    metrics.increment("cache_misses")
    
    # Try database
    db_cached = get_forecast_from_db(lat_norm, lon_norm)
    if db_cached and len(db_cached) >= 5:
        logger.info(f"DB CACHE HIT for daily forecast at {lat_norm}, {lon_norm}")
        result = [{"date": r[0], "max_temp": r[1], "min_temp": r[2], "weather_code": r[3], "sunrise": r[4], "sunset": r[5], "precipitation_sum": r[6], "precipitation_probability_max": r[7]} for r in db_cached]
        cache.set(cache_key, result)
        return result
    
    # Fetch live
    logger.info(f"CACHE MISS for daily forecast at {lat_norm}, {lon_norm}. Fetching live data...")
    live = fetch_daily_forecast(lat_norm, lon_norm)
    
    if not live:
        raise HTTPException(status_code=500, detail="Could not retrieve live forecast data.")
    
    # Cache and save
    cache.set(cache_key, live)
    save_forecast_to_db(lat_norm, lon_norm, live)
    
    return live


@app.get("/aqi-alerts")
def get_aqi_and_alerts_endpoint(request: Request, lat: float, lon: float):
    """
    Get air quality index and weather alerts for a location.
    """
    metrics = get_metrics()
    metrics.increment("total_requests")
    metrics.increment("aqi_requests")
    
    lat_norm, lon_norm = normalize_coordinates(lat, lon)
    cache_key = generate_weather_cache_key(lat_norm, lon_norm, "aqi")
    
    # Check memory cache
    cache = get_cache()
    cached_data = cache.get(cache_key)
    
    if cached_data:
        metrics.increment("cache_hits")
        logger.info(f"CACHE HIT for AQI at {lat_norm}, {lon_norm}")
        return cached_data
    
    metrics.increment("cache_misses")
    
    # Fetch live (no database caching for AQI)
    logger.info(f"Fetching AQI & Alerts data for {lat_norm}, {lon_norm}...")
    data = fetch_aqi_and_alerts(lat_norm, lon_norm)
    
    if not data["aqi"]:
        raise HTTPException(status_code=500, detail="Could not retrieve Air Quality data.")
    
    # Cache with shorter TTL (30 minutes for AQI)
    cache.set(cache_key, data, ttl=1800)
    
    return data


# ==================== ROOT ENDPOINT ====================

@app.get("/api/info")
def api_info():
    """Get API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "Production-grade weather API",
        "endpoints": {
            "weather": "/weather?lat={lat}&lon={lon}",
            "hourly": "/hourly?lat={lat}&lon={lon}",
            "forecast": "/forecast?lat={lat}&lon={lon}",
            "aqi_alerts": "/aqi-alerts?lat={lat}&lon={lon}",
            "health": "/healthz",
            "metrics": "/metrics"
        }
    }


# ==================== MOUNT STATIC FILES ====================
# Note: This should be last to avoid conflicts with API routes
app.mount("/", StaticFiles(directory="static", html=True), name="static")
