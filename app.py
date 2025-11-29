"""
IntelliWeather API - Production-Grade Weather Service

A modern, feature-rich weather API built with FastAPI featuring:
- Real-time weather data from Open-Meteo
- SQLite database for caching (main branch compatible)
- In-memory caching with TTL (fallback)
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

Phase 3 Features:
- Kubernetes deployment support
- Prometheus metrics
- Notifications (email/SMS/push)
- Growth features (analytics, referrals, shareable links)
"""

import requests
import sqlite3
import json
import os
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta, timezone

# Configuration - try to import from config.py, fall back to defaults
try:
    from config import settings
    HAS_CONFIG = True
except ImportError:
    HAS_CONFIG = False
    class DefaultSettings:
        APP_NAME = "IntelliWeather"
        APP_VERSION = "3.0.0"
        CORS_ORIGINS = ["*"]
        CORS_ALLOW_CREDENTIALS = True
        FEATURE_WEATHER_V2 = True
        FEATURE_GEOCODING = True
        FEATURE_ALERTS = True
        FEATURE_DOWNLOADS = True
        FEATURE_API_KEYS = True
        FEATURE_ML_PREDICTION = True
        FEATURE_ADMIN_DASHBOARD = True
        FEATURE_I18N = True
        FEATURE_ANALYTICS = True
        FEATURE_REFERRALS = True
        FEATURE_SHAREABLE_LINKS = True
        SENTRY_DSN = None
    settings = DefaultSettings()

# Logging - try to import from logging_config.py, fall back to print
try:
    from logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    class SimpleLogger:
        def info(self, msg): print(f"INFO: {msg}")
        def error(self, msg): print(f"ERROR: {msg}")
        def warning(self, msg): print(f"WARNING: {msg}")
    logger = SimpleLogger()

# Try to import Phase 2/3 modules (optional)
try:
    from cache import get_cache, generate_weather_cache_key, init_cache
    HAS_CACHE_MODULE = True
except ImportError:
    HAS_CACHE_MODULE = False
    def get_cache(): return None
    def generate_weather_cache_key(lat, lon, type): return f"{lat}:{lon}:{type}"
    def init_cache(): pass

try:
    from storage import get_storage, init_storage, CachedWeather
    HAS_STORAGE_MODULE = True
except ImportError:
    HAS_STORAGE_MODULE = False
    def get_storage(): return None
    def init_storage(): pass
    class CachedWeather: pass

try:
    from session_middleware import SessionMiddleware, set_session_middleware
    HAS_SESSION_MODULE = True
except ImportError:
    HAS_SESSION_MODULE = False

try:
    from middleware.rate_limiter import RateLimiterMiddleware
    HAS_RATE_LIMITER = True
except ImportError:
    HAS_RATE_LIMITER = False

try:
    from routes.auth import router as auth_router
    HAS_AUTH_ROUTER = True
except ImportError:
    HAS_AUTH_ROUTER = False

try:
    from metrics import router as metrics_router, get_metrics
    HAS_METRICS_ROUTER = True
except ImportError:
    HAS_METRICS_ROUTER = False
    class DummyMetrics:
        def increment(self, key): pass
    def get_metrics(): return DummyMetrics()

# Phase 2 routers (optional)
try:
    from routes.weather_v2 import router as weather_v2_router
    HAS_WEATHER_V2 = True
except ImportError:
    HAS_WEATHER_V2 = False

try:
    from routes.geocode import router as geocode_router
    HAS_GEOCODE = True
except ImportError:
    HAS_GEOCODE = False

try:
    from routes.alerts import router as alerts_router
    HAS_ALERTS = True
except ImportError:
    HAS_ALERTS = False

try:
    from routes.downloads import router as downloads_router
    HAS_DOWNLOADS = True
except ImportError:
    HAS_DOWNLOADS = False

try:
    from routes.apikeys import router as apikeys_router
    HAS_APIKEYS = True
except ImportError:
    HAS_APIKEYS = False

try:
    from routes.predict import router as predict_router
    HAS_PREDICT = True
except ImportError:
    HAS_PREDICT = False

try:
    from routes.admin import router as admin_router
    HAS_ADMIN = True
except ImportError:
    HAS_ADMIN = False

try:
    from routes.i18n import router as i18n_router
    HAS_I18N = True
except ImportError:
    HAS_I18N = False

try:
    from routes.growth import router as growth_router
    HAS_GROWTH = True
except ImportError:
    HAS_GROWTH = False


# ==================== DATABASE CONFIGURATION (Main Branch Compatible) ====================
DB_FILE = "weather.db"


def init_db():
    """Initialize the SQLite database with necessary tables."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Weather Readings Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather_readings (
                location_name TEXT,
                latitude REAL,
                longitude REAL,
                timestamp TEXT,
                temperature_c REAL,
                humidity_pct REAL,
                pressure_hpa REAL,
                wind_speed_mps REAL,
                precip_mm REAL,
                weather_code INTEGER,
                apparent_temperature REAL,
                uv_index REAL,
                is_day INTEGER,
                PRIMARY KEY (location_name, timestamp)
            );
        """)
        
        # Hourly Forecasts Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hourly_forecasts (
                latitude REAL,
                longitude REAL,
                forecast_time TEXT,
                temperature_c REAL,
                precipitation_prob REAL,
                wind_speed_mps REAL,
                cloud_cover REAL,
                weather_code INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (latitude, longitude, forecast_time)
            );
        """)
        
        # Daily Forecasts Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_forecasts (
                latitude REAL,
                longitude REAL,
                forecast_date TEXT,
                max_temp_c REAL,
                min_temp_c REAL,
                weather_code INTEGER,
                sunrise TEXT,
                sunset TEXT,
                precipitation_sum REAL,
                precipitation_probability_max REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (latitude, longitude, forecast_date)
            );
        """)
        
        conn.commit()
        conn.close()
        logger.info("✅ Local SQLite database initialized.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")


# ==================== APPLICATION LIFECYCLE ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Initialize SQLite database (main branch compatible)
    init_db()
    
    # Initialize Phase 2 components (if available)
    if HAS_STORAGE_MODULE:
        init_storage()
    if HAS_CACHE_MODULE:
        init_cache()
    
    # Initialize Sentry if configured
    if getattr(settings, 'SENTRY_DSN', None):
        try:
            import sentry_sdk
            sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.1)
            logger.info("Sentry initialized")
        except ImportError:
            logger.warning("Sentry SDK not installed")
    
    print("=" * 70)
    print("✅ SERVER STARTED SUCCESSFULLY!")
    print("=" * 70)
    print("📍 Local: http://localhost:8000")
    print("🌐 Codespaces: Check PORTS tab for the forwarded URL")
    print("=" * 70)
    print("\n🔧 API Endpoints:")
    print("   GET /weather?lat={lat}&lon={lon}")
    print("   GET /hourly?lat={lat}&lon={lon}")
    print("   GET /forecast?lat={lat}&lon={lon}")
    print("   GET /aqi-alerts?lat={lat}&lon={lon}")
    print("   GET /api-test (health check)")
    print("=" * 70 + "\n")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    if HAS_CACHE_MODULE:
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

Production-grade weather API with SQLite caching, authentication, and rate limiting.

## Features
- Real-time weather data
- SQLite database caching
- Session-based authentication  
- Rate limiting
- Health & metrics
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
    allow_origins=getattr(settings, 'CORS_ORIGINS', ["*"]),
    allow_credentials=getattr(settings, 'CORS_ALLOW_CREDENTIALS', True),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiter middleware (if available)
if HAS_RATE_LIMITER:
    app.add_middleware(RateLimiterMiddleware)

# Add session middleware (if available)
if HAS_SESSION_MODULE:
    session_middleware = SessionMiddleware(app)
    set_session_middleware(session_middleware)

# Include Phase 1 routers (if available)
if HAS_AUTH_ROUTER:
    app.include_router(auth_router)
if HAS_METRICS_ROUTER:
    app.include_router(metrics_router)

# Include Phase 2 routers (conditionally based on feature flags)
if HAS_WEATHER_V2 and getattr(settings, 'FEATURE_WEATHER_V2', True):
    app.include_router(weather_v2_router)
    logger.info("Weather V2 routes enabled")

if HAS_GEOCODE and getattr(settings, 'FEATURE_GEOCODING', True):
    app.include_router(geocode_router)
    logger.info("Geocoding routes enabled")

if HAS_ALERTS and getattr(settings, 'FEATURE_ALERTS', True):
    app.include_router(alerts_router)
    logger.info("Alerts routes enabled")

if HAS_DOWNLOADS and getattr(settings, 'FEATURE_DOWNLOADS', True):
    app.include_router(downloads_router)
    logger.info("Downloads routes enabled")

if HAS_APIKEYS and getattr(settings, 'FEATURE_API_KEYS', True):
    app.include_router(apikeys_router)
    logger.info("API Keys routes enabled")

if HAS_PREDICT and getattr(settings, 'FEATURE_ML_PREDICTION', True):
    app.include_router(predict_router)
    logger.info("ML Prediction routes enabled")

if HAS_ADMIN and getattr(settings, 'FEATURE_ADMIN_DASHBOARD', True):
    app.include_router(admin_router)
    logger.info("Admin dashboard routes enabled")

if HAS_I18N and getattr(settings, 'FEATURE_I18N', True):
    app.include_router(i18n_router)
    logger.info("i18n routes enabled")

# Phase 3: Growth features
if HAS_GROWTH and (getattr(settings, 'FEATURE_ANALYTICS', True) or 
                   getattr(settings, 'FEATURE_REFERRALS', True) or 
                   getattr(settings, 'FEATURE_SHAREABLE_LINKS', True)):
    app.include_router(growth_router)
    logger.info("Growth routes enabled")


# ==================== HELPER FUNCTIONS (Main Branch Compatible) ====================

def normalize_coordinates(lat: float, lon: float) -> tuple:
    """Normalize coordinates to 2 decimal places for caching."""
    return round(lat, 2), round(lon, 2)


# --- CURRENT WEATHER ---
def get_weather_from_db(lat, lon):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        query = "SELECT * FROM weather_readings WHERE latitude = ? AND longitude = ? AND timestamp >= ? ORDER BY timestamp DESC LIMIT 1;"
        cursor.execute(query, (lat, lon, one_hour_ago))
        result = cursor.fetchone()
        conn.close()
        return result
    except Exception as e:
        logger.warning(f"DB Error (get_weather): {e}")
        return None


def save_weather_to_db(data_rows):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        insert_query = "INSERT OR IGNORE INTO weather_readings (location_name, latitude, longitude, timestamp, temperature_c, humidity_pct, pressure_hpa, wind_speed_mps, precip_mm, weather_code, apparent_temperature, uv_index, is_day) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"
        for row in data_rows:
            timestamp_val = row['timestamp']
            if isinstance(timestamp_val, datetime):
                timestamp_val = timestamp_val.isoformat()
            values = (row['location_name'], row['latitude'], row['longitude'], timestamp_val, row['temperature_c'], row['humidity_pct'], row['pressure_hpa'], row['wind_speed_mps'], row['precip_mm'], row['weather_code'], row['apparent_temperature'], row['uv_index'], row['is_day'])
            cursor.execute(insert_query, values)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"DB Error (save_weather): {e}")


def fetch_live_weather(lat, lon):
    try:
        api_url = "https://api.open-meteo.com/v1/forecast"
        params = {"latitude": lat, "longitude": lon, "current": "temperature_2m,apparent_temperature,precipitation,weather_code,relative_humidity_2m,wind_speed_10m,uv_index,pressure_msl,is_day", "timezone": "auto"}
        response = requests.get(api_url, params=params, timeout=10)
        if response.status_code != 200:
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
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout fetching weather for {lat}, {lon}")
        return None
    except Exception as e:
        logger.error(f"Error fetching weather: {e}")
        return None


# --- HOURLY FORECAST ---
def get_hourly_forecast_from_db(lat, lon):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        six_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
        query = "SELECT forecast_time, temperature_c, precipitation_prob, wind_speed_mps, cloud_cover, weather_code FROM hourly_forecasts WHERE latitude = ? AND longitude = ? AND created_at >= ? ORDER BY forecast_time ASC LIMIT 24;"
        cursor.execute(query, (lat, lon, six_hours_ago))
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        logger.warning(f"DB Error (get_hourly): {e}")
        return None


def save_hourly_forecast_to_db(lat, lon, forecast_data):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        query = """
            INSERT INTO hourly_forecasts (latitude, longitude, forecast_time, temperature_c, precipitation_prob, wind_speed_mps, cloud_cover, weather_code, created_at) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) 
            ON CONFLICT(latitude, longitude, forecast_time) DO UPDATE SET 
            temperature_c = excluded.temperature_c, 
            precipitation_prob = excluded.precipitation_prob, 
            wind_speed_mps = excluded.wind_speed_mps, 
            cloud_cover = excluded.cloud_cover, 
            weather_code = excluded.weather_code, 
            created_at = excluded.created_at;
        """
        now_str = datetime.now(timezone.utc).isoformat()
        for hour in forecast_data:
            values = (lat, lon, hour['time'], hour['temp'], hour['precip_prob'], hour['wind'], hour['cloud_cover'], hour['weather_code'], now_str)
            cursor.execute(query, values)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"DB Error (save_hourly): {e}")


def fetch_hourly_forecast(lat, lon):
    try:
        api_url = "https://api.open-meteo.com/v1/forecast"
        params = {"latitude": lat, "longitude": lon, "hourly": "temperature_2m,precipitation_probability,weather_code,wind_speed_10m,cloud_cover", "forecast_days": 1, "timezone": "auto"}
        response = requests.get(api_url, params=params, timeout=10)
        if response.status_code != 200:
            return None
        raw = response.json()['hourly']
        return [{"time": raw['time'][i], "temp": raw['temperature_2m'][i], "precip_prob": raw['precipitation_probability'][i], "wind": round(raw['wind_speed_10m'][i] / 3.6, 2), "cloud_cover": raw['cloud_cover'][i], "weather_code": raw['weather_code'][i]} for i in range(len(raw['time']))]
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout fetching hourly forecast for {lat}, {lon}")
        return None
    except Exception as e:
        logger.error(f"Error fetching hourly forecast: {e}")
        return None


# --- DAILY FORECAST ---
def get_forecast_from_db(lat, lon):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        six_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
        query = "SELECT forecast_date, max_temp_c, min_temp_c, weather_code, sunrise, sunset, precipitation_sum, precipitation_probability_max FROM daily_forecasts WHERE latitude = ? AND longitude = ? AND created_at >= ? ORDER BY forecast_date ASC;"
        cursor.execute(query, (lat, lon, six_hours_ago))
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        logger.warning(f"DB Error (get_forecast): {e}")
        return None


def save_forecast_to_db(lat, lon, forecast_data):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        query = """
            INSERT INTO daily_forecasts (latitude, longitude, forecast_date, max_temp_c, min_temp_c, weather_code, sunrise, sunset, precipitation_sum, precipitation_probability_max, created_at) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) 
            ON CONFLICT(latitude, longitude, forecast_date) DO UPDATE SET 
            max_temp_c = excluded.max_temp_c, 
            min_temp_c = excluded.min_temp_c, 
            weather_code = excluded.weather_code, 
            sunrise = excluded.sunrise, 
            sunset = excluded.sunset, 
            precipitation_sum = excluded.precipitation_sum, 
            precipitation_probability_max = excluded.precipitation_probability_max, 
            created_at = excluded.created_at;
        """
        now_str = datetime.now(timezone.utc).isoformat()
        for day in forecast_data:
            values = (lat, lon, day['date'], day['max_temp'], day['min_temp'], day['weather_code'], day['sunrise'], day['sunset'], day['precipitation_sum'], day['precipitation_probability_max'], now_str)
            cursor.execute(query, values)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"DB Error (save_forecast): {e}")


def fetch_daily_forecast(lat, lon):
    try:
        api_url = "https://api.open-meteo.com/v1/forecast"
        params = {"latitude": lat, "longitude": lon, "daily": "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,precipitation_sum,precipitation_probability_max", "forecast_days": 7, "timezone": "auto"}
        response = requests.get(api_url, params=params, timeout=10)
        if response.status_code != 200:
            return None
        raw = response.json()['daily']
        return [{"date": raw['time'][i], "max_temp": raw['temperature_2m_max'][i], "min_temp": raw['temperature_2m_min'][i], "weather_code": raw['weather_code'][i], "sunrise": raw['sunrise'][i], "sunset": raw['sunset'][i], "precipitation_sum": raw['precipitation_sum'][i], "precipitation_probability_max": raw['precipitation_probability_max'][i]} for i in range(len(raw['time']))]
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout fetching daily forecast for {lat}, {lon}")
        return None
    except Exception as e:
        logger.error(f"Error fetching daily forecast: {e}")
        return None


# --- AQI & ALERTS ---
def fetch_aqi_and_alerts(lat, lon):
    try:
        air_quality_api_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        forecast_api_url = "https://api.open-meteo.com/v1/forecast"
        aqi_params = {"latitude": lat, "longitude": lon, "hourly": "us_aqi,pm2_5,carbon_monoxide,ozone", "timezone": "auto"}
        alerts_params = {"latitude": lat, "longitude": lon, "daily": "weather_code", "forecast_days": 1}

        aqi_response = requests.get(air_quality_api_url, params=aqi_params, timeout=10)
        alerts_response = requests.get(forecast_api_url, params=alerts_params, timeout=10)
        
        aqi_data = aqi_response.json() if aqi_response.status_code == 200 else None
        alerts = alerts_response.json().get("daily", {}).get("alerts", []) if alerts_response.status_code == 200 else []
        
        return {"aqi": aqi_data, "alerts": alerts}
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout fetching AQI/alerts for {lat}, {lon}")
        return {"aqi": None, "alerts": []}
    except Exception as e:
        logger.error(f"Error fetching AQI/alerts: {e}")
        return {"aqi": None, "alerts": []}


# ==================== API ENDPOINTS (Main Branch Compatible) ====================

@app.get("/weather", tags=["Weather"])
def get_weather(lat: float, lon: float):
    """Get current weather for a location."""
    metrics = get_metrics()
    metrics.increment("total_requests")
    metrics.increment("weather_requests")
    
    logger.info(f"GET /weather request for: {lat}, {lon}")
    
    # Normalize coordinates
    lat_norm, lon_norm = normalize_coordinates(lat, lon)
    
    # Check in-memory cache first (if available)
    if HAS_CACHE_MODULE:
        cache = get_cache()
        cache_key = generate_weather_cache_key(lat_norm, lon_norm, "current")
        cached_data = cache.get(cache_key) if cache else None
        if cached_data:
            metrics.increment("cache_hits")
            logger.info(f"MEMORY CACHE HIT for current weather at {lat_norm}, {lon_norm}")
            return {"source": "cache", **cached_data}
    
    # Check SQLite database cache
    cached = get_weather_from_db(lat_norm, lon_norm)
    if cached and len(cached) >= 13:
        metrics.increment("cache_hits")
        logger.info(f"DB CACHE HIT for current weather at {lat_norm}, {lon_norm}")
        return {
            "source": "cache", 
            "location_name": cached[0],
            "latitude": cached[1],
            "longitude": cached[2],
            "timestamp": cached[3], 
            "temperature_c": cached[4], 
            "humidity_pct": cached[5], 
            "pressure_hpa": cached[6], 
            "wind_speed_mps": cached[7], 
            "precip_mm": cached[8], 
            "weather_code": cached[9], 
            "apparent_temperature": cached[10], 
            "uv_index": cached[11], 
            "is_day": cached[12]
        }
    
    metrics.increment("cache_misses")
    logger.info(f"CACHE MISS for current weather at {lat_norm}, {lon_norm}. Fetching live data...")
    
    # Fetch live data
    live = fetch_live_weather(lat_norm, lon_norm)
    if not live:
        logger.warning(f"Failed to fetch weather data for {lat_norm}, {lon_norm}, returning fallback")
        return {
            "source": "unavailable",
            "location_name": f"Lat_{lat}_Lon_{lon}",
            "latitude": lat,
            "longitude": lon,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "temperature_c": 0,
            "humidity_pct": 0,
            "pressure_hpa": 0,
            "wind_speed_mps": 0,
            "precip_mm": 0,
            "weather_code": 0,
            "apparent_temperature": 0,
            "uv_index": 0,
            "is_day": 1
        }
    
    # Save to SQLite database
    save_weather_to_db([live])
    
    # Save to in-memory cache (if available)
    if HAS_CACHE_MODULE:
        cache = get_cache()
        if cache:
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
            cache_key = generate_weather_cache_key(lat_norm, lon_norm, "current")
            cache.set(cache_key, result)
    
    # Prepare response
    response = {**live}
    if 'timestamp' in response and isinstance(response['timestamp'], datetime):
        response['timestamp'] = response['timestamp'].isoformat()
    return {"source": "live", **response}


@app.get("/hourly", tags=["Weather"])
def get_hourly_forecast_endpoint(lat: float, lon: float):
    """Get hourly forecast for a location."""
    metrics = get_metrics()
    metrics.increment("total_requests")
    metrics.increment("hourly_requests")
    
    lat_norm, lon_norm = normalize_coordinates(lat, lon)
    
    # Check SQLite database cache
    cached = get_hourly_forecast_from_db(lat_norm, lon_norm)
    if cached and len(cached) >= 24:
        metrics.increment("cache_hits")
        logger.info(f"CACHE HIT for hourly forecast at {lat_norm}, {lon_norm}")
        return [{"time": r[0], "temp": r[1], "precip_prob": r[2], "wind": r[3], "cloud_cover": r[4], "weather_code": r[5]} for r in cached]
    
    metrics.increment("cache_misses")
    logger.info(f"CACHE MISS for hourly forecast at {lat_norm}, {lon_norm}. Fetching live data...")
    
    live = fetch_hourly_forecast(lat_norm, lon_norm)
    if not live:
        logger.warning(f"Failed to fetch hourly data for {lat_norm}, {lon_norm}, returning empty array")
        return []
    
    save_hourly_forecast_to_db(lat_norm, lon_norm, live)
    return live


@app.get("/forecast", tags=["Weather"])
def get_daily_forecast_endpoint(lat: float, lon: float):
    """Get 7-day forecast for a location."""
    metrics = get_metrics()
    metrics.increment("total_requests")
    metrics.increment("forecast_requests")
    
    lat_norm, lon_norm = normalize_coordinates(lat, lon)
    
    # Check SQLite database cache
    cached = get_forecast_from_db(lat_norm, lon_norm)
    if cached and len(cached) >= 5:
        metrics.increment("cache_hits")
        logger.info(f"CACHE HIT for 5-day forecast at {lat_norm}, {lon_norm}")
        return [{"date": r[0], "max_temp": r[1], "min_temp": r[2], "weather_code": r[3], "sunrise": r[4], "sunset": r[5], "precipitation_sum": r[6], "precipitation_probability_max": r[7]} for r in cached]
    
    metrics.increment("cache_misses")
    logger.info(f"CACHE MISS for 5-day forecast at {lat_norm}, {lon_norm}. Fetching live data...")
    
    live = fetch_daily_forecast(lat_norm, lon_norm)
    if not live:
        logger.warning(f"Failed to fetch forecast data for {lat_norm}, {lon_norm}, returning empty array")
        return []
    
    save_forecast_to_db(lat_norm, lon_norm, live)
    return live


@app.get("/aqi-alerts", tags=["Weather"])
def get_aqi_and_alerts_endpoint(lat: float, lon: float):
    """Get air quality index and weather alerts for a location."""
    metrics = get_metrics()
    metrics.increment("total_requests")
    metrics.increment("aqi_requests")
    
    lat_norm, lon_norm = normalize_coordinates(lat, lon)
    logger.info(f"Fetching AQI & Alerts data for {lat_norm}, {lon_norm}...")
    
    data = fetch_aqi_and_alerts(lat_norm, lon_norm)
    return data if data else {"aqi": None, "alerts": []}


@app.get("/api-test", tags=["Health"])
def api_test():
    """Simple endpoint to verify API is working."""
    return {"status": "ok", "message": "Weather API is running!", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/info", tags=["Health"])
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
