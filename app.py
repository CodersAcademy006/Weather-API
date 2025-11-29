# Save this file as "app.py"
import requests
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta, timezone

# --- Configuration & Initialization ---
DB_FILE = "weather.db"
app = FastAPI()

@app.on_event("startup")
async def startup_event():
    init_db()
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

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# ====================================================================
#  HELPER FUNCTIONS
# ====================================================================

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
        print("✅ Local SQLite database initialized.")
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")

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
        print(f"⚠️ DB Error (get_weather): {e}")
        return None

def save_weather_to_db(data_rows):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        insert_query = "INSERT OR IGNORE INTO weather_readings (location_name, latitude, longitude, timestamp, temperature_c, humidity_pct, pressure_hpa, wind_speed_mps, precip_mm, weather_code, apparent_temperature, uv_index, is_day) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"
        for row in data_rows:
            values = (row['location_name'], row['latitude'], row['longitude'], row['timestamp'].isoformat(), row['temperature_c'], row['humidity_pct'], row['pressure_hpa'], row['wind_speed_mps'], row['precip_mm'], row['weather_code'], row['apparent_temperature'], row['uv_index'], row['is_day'])
            cursor.execute(insert_query, values)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ DB Error (save_weather): {e}")

def fetch_live_weather(lat, lon):
    try:
        api_url = "https://api.open-meteo.com/v1/forecast"
        params = {"latitude": lat, "longitude": lon, "current": "temperature_2m,apparent_temperature,precipitation,weather_code,relative_humidity_2m,wind_speed_10m,uv_index,pressure_msl,is_day", "timezone": "auto"}
        response = requests.get(api_url, params=params, timeout=10)
        if response.status_code != 200: return None
        raw = response.json()['current']
        return { "location_name": f"Lat_{lat}_Lon_{lon}", "latitude": lat, "longitude": lon, "timestamp": datetime.fromisoformat(raw['time']), "temperature_c": raw['temperature_2m'], "humidity_pct": raw['relative_humidity_2m'], "pressure_hpa": raw['pressure_msl'], "wind_speed_mps": round(raw['wind_speed_10m'] / 3.6, 2), "precip_mm": raw['precipitation'], "weather_code": raw['weather_code'], "apparent_temperature": raw['apparent_temperature'], "uv_index": raw['uv_index'], "is_day": raw['is_day'] }
    except requests.exceptions.Timeout:
        print(f"⏱️ Timeout fetching weather for {lat}, {lon}")
        return None
    except Exception as e:
        print(f"❌ Error fetching weather: {e}")
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
        print(f"⚠️ DB Error (get_hourly): {e}")
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
        print(f"⚠️ DB Error (save_hourly): {e}")

def fetch_hourly_forecast(lat, lon):
    try:
        api_url = "https://api.open-meteo.com/v1/forecast"
        params = { "latitude": lat, "longitude": lon, "hourly": "temperature_2m,precipitation_probability,weather_code,wind_speed_10m,cloud_cover", "forecast_days": 1, "timezone": "auto" }
        response = requests.get(api_url, params=params, timeout=10)
        if response.status_code != 200: return None
        raw = response.json()['hourly']
        return [{ "time": raw['time'][i], "temperature_c": raw['temperature_2m'][i], "precipitation_prob": raw['precipitation_probability'][i], "wind_speed_mps": round(raw['wind_speed_10m'][i] / 3.6, 2), "cloud_cover": raw['cloud_cover'][i], "weather_code": raw['weather_code'][i] } for i in range(len(raw['time']))]
    except requests.exceptions.Timeout:
        print(f"⏱️ Timeout fetching hourly forecast for {lat}, {lon}")
        return None
    except Exception as e:
        print(f"❌ Error fetching hourly forecast: {e}")
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
        print(f"⚠️ DB Error (get_forecast): {e}")
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
        print(f"⚠️ DB Error (save_forecast): {e}")

def fetch_daily_forecast(lat, lon):
    try:
        api_url = "https://api.open-meteo.com/v1/forecast"
        params = { "latitude": lat, "longitude": lon, "daily": "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,precipitation_sum,precipitation_probability_max", "forecast_days": 7, "timezone": "auto" }
        response = requests.get(api_url, params=params, timeout=10)
        if response.status_code != 200: return None
        raw = response.json()['daily']
        return [{"date": raw['time'][i], "max_temp": raw['temperature_2m_max'][i], "min_temp": raw['temperature_2m_min'][i], "weather_code": raw['weather_code'][i], "sunrise": raw['sunrise'][i], "sunset": raw['sunset'][i], "precipitation_sum": raw['precipitation_sum'][i], "precipitation_probability_max": raw['precipitation_probability_max'][i]} for i in range(len(raw['time']))]
    except requests.exceptions.Timeout:
        print(f"⏱️ Timeout fetching daily forecast for {lat}, {lon}")
        return None
    except Exception as e:
        print(f"❌ Error fetching daily forecast: {e}")
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
        # Alerts are still experimental and may not always be present
        alerts = alerts_response.json().get("daily", {}).get("alerts", []) if alerts_response.status_code == 200 else []
        
        return {"aqi": aqi_data, "alerts": alerts}
    except requests.exceptions.Timeout:
        print(f"⏱️ Timeout fetching AQI/alerts for {lat}, {lon}")
        return {"aqi": None, "alerts": []}
    except Exception as e:
        print(f"❌ Error fetching AQI/alerts: {e}")
        return {"aqi": None, "alerts": []}

# ====================================================================
#  API ENDPOINTS
# ====================================================================

@app.get("/weather")
def get_weather(lat: float, lon: float):
    print(f"📥 GET /weather request for: {lat}, {lon}")
    cached = get_weather_from_db(lat, lon)
    if cached and len(cached) >= 13:
        print(f"✅ CACHE HIT for current weather at {lat}, {lon}")
        # SQLite row: (location_name, latitude, longitude, timestamp, temperature_c, humidity_pct, pressure_hpa, wind_speed_mps, precip_mm, weather_code, apparent_temperature, uv_index, is_day)
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
    print(f"🌐 CACHE MISS for current weather at {lat}, {lon}. Fetching live data...")
    live = fetch_live_weather(lat, lon)
    if not live: 
        print(f"⚠️ Failed to fetch weather data for {lat}, {lon}, returning fallback")
        # Return minimal fallback data instead of crashing
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
    save_weather_to_db([live])
    # Convert timestamp to string for JSON serialization
    response = {**live}
    if 'timestamp' in response and isinstance(response['timestamp'], datetime):
        response['timestamp'] = response['timestamp'].isoformat()
    return {"source": "live", **response}

@app.get("/hourly")
def get_hourly_forecast(lat: float, lon: float):
    cached = get_hourly_forecast_from_db(lat, lon)
    if cached and len(cached) >= 24:
        print(f"✅ CACHE HIT for hourly forecast at {lat}, {lon}")
        # SQLite row: (forecast_time, temperature_c, precipitation_prob, wind_speed_mps, cloud_cover, weather_code)
        return [{"time": r[0], "temp": r[1], "precip_prob": r[2], "wind": r[3], "cloud_cover": r[4], "weather_code": r[5]} for r in cached]
    print(f"🌐 CACHE MISS for hourly forecast at {lat}, {lon}. Fetching live data...")
    live = fetch_hourly_forecast(lat, lon)
    if not live:
        print(f"⚠️ Failed to fetch hourly data for {lat}, {lon}, returning empty array")
        return []  # Return empty array instead of raising error
    save_hourly_forecast_to_db(lat, lon, live)
    return live

@app.get("/forecast")
def get_daily_forecast(lat: float, lon: float):
    cached = get_forecast_from_db(lat, lon)
    if cached and len(cached) >= 5:
        print(f"✅ CACHE HIT for 5-day forecast at {lat}, {lon}")
        # SQLite row: (forecast_date, max_temp_c, min_temp_c, weather_code, sunrise, sunset, precipitation_sum, precipitation_probability_max)
        return [{"date": r[0], "max_temp": r[1], "min_temp": r[2], "weather_code": r[3], "sunrise": r[4], "sunset": r[5], "precipitation_sum": r[6], "precipitation_probability_max": r[7]} for r in cached]
    print(f"🌐 CACHE MISS for 5-day forecast at {lat}, {lon}. Fetching live data...")
    live = fetch_daily_forecast(lat, lon)
    if not live: 
        print(f"⚠️ Failed to fetch forecast data for {lat}, {lon}, returning empty array")
        return []  # Return empty array instead of raising error
    save_forecast_to_db(lat, lon, live)
    return live

@app.get("/aqi-alerts")
def get_aqi_and_alerts(lat: float, lon: float):
    # Caching is not implemented for this endpoint in the prototype
    print(f"Fetching AQI & Alerts data for {lat}, {lon}...")
    data = fetch_aqi_and_alerts(lat, lon)
    # Always return a valid structure, even if aqi is None
    return data if data else {"aqi": None, "alerts": []}

@app.get("/api-test")
def api_test():
    """Simple endpoint to verify API is working"""
    return {"status": "ok", "message": "Weather API is running!", "timestamp": datetime.now(timezone.utc).isoformat()}

# --- Mount the Static Files (Frontend) ---
# IMPORTANT: This MUST be last, after all API routes, or it will override them!
app.mount("/", StaticFiles(directory="static", html=True), name="static")
