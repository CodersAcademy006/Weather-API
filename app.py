# Save this file as "app.py"
import requests
import psycopg2
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta, timezone

# --- Configuration & Initialization ---
DB_CONNECTION_STRING = "postgresql://postgres.kucoxmriguvqulnkzpcw:S.La9c4vc#wE2gq@aws-1-ap-south-1.pooler.supabase.com:6543/postgres"
app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# ====================================================================
#  HELPER FUNCTIONS
# ====================================================================

# --- CURRENT WEATHER ---
def get_weather_from_db(lat, lon):
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cursor = conn.cursor()
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    query = "SELECT * FROM weather_readings WHERE latitude = %s AND longitude = %s AND timestamp >= %s ORDER BY timestamp DESC LIMIT 1;"
    cursor.execute(query, (lat, lon, one_hour_ago))
    result = cursor.fetchone()
    conn.close()
    return result

def save_weather_to_db(data_rows):
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cursor = conn.cursor()
    insert_query = "INSERT INTO weather_readings (location_name, latitude, longitude, timestamp, temperature_c, humidity_pct, pressure_hpa, wind_speed_mps, precip_mm, weather_code, apparent_temperature, uv_index, is_day) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (location_name, timestamp) DO NOTHING;"
    for row in data_rows:
        values = (row['location_name'], row['latitude'], row['longitude'], row['timestamp'], row['temperature_c'], row['humidity_pct'], row['pressure_hpa'], row['wind_speed_mps'], row['precip_mm'], row['weather_code'], row['apparent_temperature'], row['uv_index'], row['is_day'])
        cursor.execute(insert_query, values)
    conn.commit()
    conn.close()

def fetch_live_weather(lat, lon):
    api_url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": lat, "longitude": lon, "current": "temperature_2m,apparent_temperature,precipitation,weather_code,relative_humidity_2m,wind_speed_10m,uv_index,pressure_msl,is_day", "timezone": "auto"}
    response = requests.get(api_url, params=params)
    if response.status_code != 200: return None
    raw = response.json()['current']
    return { "location_name": f"Lat_{lat}_Lon_{lon}", "latitude": lat, "longitude": lon, "timestamp": datetime.fromisoformat(raw['time']), "temperature_c": raw['temperature_2m'], "humidity_pct": raw['relative_humidity_2m'], "pressure_hpa": raw['pressure_msl'], "wind_speed_mps": round(raw['wind_speed_10m'] / 3.6, 2), "precip_mm": raw['precipitation'], "weather_code": raw['weather_code'], "apparent_temperature": raw['apparent_temperature'], "uv_index": raw['uv_index'], "is_day": raw['is_day'] }

# --- HOURLY FORECAST ---
def get_hourly_forecast_from_db(lat, lon):
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cursor = conn.cursor()
    six_hours_ago = datetime.now(timezone.utc) - timedelta(hours=6)
    query = "SELECT forecast_time, temperature_c, precipitation_prob, wind_speed_mps, cloud_cover, weather_code FROM hourly_forecasts WHERE latitude = %s AND longitude = %s AND created_at >= %s ORDER BY forecast_time ASC LIMIT 24;"
    cursor.execute(query, (lat, lon, six_hours_ago))
    results = cursor.fetchall()
    conn.close()
    return results

def save_hourly_forecast_to_db(lat, lon, forecast_data):
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cursor = conn.cursor()
    query = "INSERT INTO hourly_forecasts (latitude, longitude, forecast_time, temperature_c, precipitation_prob, wind_speed_mps, cloud_cover, weather_code) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (latitude, longitude, forecast_time) DO UPDATE SET temperature_c = EXCLUDED.temperature_c, precipitation_prob = EXCLUDED.precipitation_prob, wind_speed_mps = EXCLUDED.wind_speed_mps, cloud_cover = EXCLUDED.cloud_cover, weather_code = EXCLUDED.weather_code, created_at = NOW();"
    for hour in forecast_data:
        values = (lat, lon, hour['time'], hour['temp'], hour['precip_prob'], hour['wind'], hour['cloud_cover'], hour['weather_code'])
        cursor.execute(query, values)
    conn.commit()
    conn.close()

def fetch_hourly_forecast(lat, lon):
    api_url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": lat, "longitude": lon, "hourly": "temperature_2m,precipitation_probability,wind_speed_10m,cloud_cover,weather_code", "forecast_days": 1, "timezone": "auto"}
    response = requests.get(api_url, params=params)
    if response.status_code != 200: return None
    raw = response.json()['hourly']
    return [{"time": raw['time'][i], "temp": raw['temperature_2m'][i], "precip_prob": raw['precipitation_probability'][i], "wind": round(raw['wind_speed_10m'][i] / 3.6, 2), "cloud_cover": raw['cloud_cover'][i], "weather_code": raw['weather_code'][i]} for i in range(len(raw['time']))]

# --- DAILY FORECAST ---
def get_forecast_from_db(lat, lon):
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cursor = conn.cursor()
    six_hours_ago = datetime.now(timezone.utc) - timedelta(hours=6)
    query = "SELECT forecast_date, max_temp_c, min_temp_c, weather_code, sunrise, sunset, precipitation_sum, precipitation_probability_max FROM daily_forecasts WHERE latitude = %s AND longitude = %s AND created_at >= %s ORDER BY forecast_date ASC;"
    cursor.execute(query, (lat, lon, six_hours_ago))
    results = cursor.fetchall()
    conn.close()
    return results

def save_forecast_to_db(lat, lon, forecast_data):
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cursor = conn.cursor()
    query = "INSERT INTO daily_forecasts (latitude, longitude, forecast_date, max_temp_c, min_temp_c, weather_code, sunrise, sunset, precipitation_sum, precipitation_probability_max) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (latitude, longitude, forecast_date) DO UPDATE SET max_temp_c = EXCLUDED.max_temp_c, min_temp_c = EXCLUDED.min_temp_c, weather_code = EXCLUDED.weather_code, sunrise = EXCLUDED.sunrise, sunset = EXCLUDED.sunset, precipitation_sum = EXCLUDED.precipitation_sum, precipitation_probability_max = EXCLUDED.precipitation_probability_max, created_at = NOW();"
    for day in forecast_data:
        values = (lat, lon, day['date'], day['max_temp'], day['min_temp'], day['weather_code'], day['sunrise'], day['sunset'], day['precipitation_sum'], day['precipitation_probability_max'])
        cursor.execute(query, values)
    conn.commit()
    conn.close()

def fetch_daily_forecast(lat, lon):
    api_url = "https://api.open-meteo.com/v1/forecast"
    params = { "latitude": lat, "longitude": lon, "daily": "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,precipitation_sum,precipitation_probability_max", "forecast_days": 7, "timezone": "auto" }
    response = requests.get(api_url, params=params)
    if response.status_code != 200: return None
    raw = response.json()['daily']
    return [{"date": raw['time'][i], "max_temp": raw['temperature_2m_max'][i], "min_temp": raw['temperature_2m_min'][i], "weather_code": raw['weather_code'][i], "sunrise": raw['sunrise'][i], "sunset": raw['sunset'][i], "precipitation_sum": raw['precipitation_sum'][i], "precipitation_probability_max": raw['precipitation_probability_max'][i]} for i in range(len(raw['time']))]

# --- AQI & ALERTS ---
def fetch_aqi_and_alerts(lat, lon):
    air_quality_api_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    forecast_api_url = "https://api.open-meteo.com/v1/forecast"
    aqi_params = {"latitude": lat, "longitude": lon, "hourly": "us_aqi,pm2_5,carbon_monoxide,ozone", "timezone": "auto"}
    alerts_params = {"latitude": lat, "longitude": lon, "daily": "weather_code", "forecast_days": 1}

    aqi_response = requests.get(air_quality_api_url, params=aqi_params)
    alerts_response = requests.get(forecast_api_url, params=alerts_params)
    
    aqi_data = aqi_response.json() if aqi_response.status_code == 200 else None
    # Alerts are still experimental and may not always be present
    alerts = alerts_response.json().get("daily", {}).get("alerts", []) if alerts_response.status_code == 200 else []
    
    return {"aqi": aqi_data, "alerts": alerts}

# ====================================================================
#  API ENDPOINTS
# ====================================================================

@app.get("/weather")
def get_weather(lat: float, lon: float):
    cached = get_weather_from_db(lat, lon)
    if cached and len(cached) >= 14:
        print(f"CACHE HIT for current weather at {lat}, {lon}")
        return {"source": "cache", "timestamp": cached[4], "temperature_c": cached[5], "humidity_pct": cached[6], "pressure_hpa": cached[7], "wind_speed_mps": cached[8], "precip_mm": cached[9], "weather_code": cached[10], "apparent_temperature": cached[11], "uv_index": cached[12], "is_day": cached[13]}
    print(f"CACHE MISS for current weather at {lat}, {lon}. Fetching live data...")
    live = fetch_live_weather(lat, lon)
    if not live: raise HTTPException(status_code=500, detail="Could not retrieve live weather data.")
    save_weather_to_db([live])
    return {"source": "live", **live}

@app.get("/hourly")
def get_hourly_forecast(lat: float, lon: float):
    cached = get_hourly_forecast_from_db(lat, lon)
    if cached and len(cached) >= 24:
        print(f"CACHE HIT for hourly forecast at {lat}, {lon}")
        return [{"time": r[0], "temp": r[1], "precip_prob": r[2], "wind": r[3], "cloud_cover": r[4], "weather_code": r[5]} for r in cached]
    print(f"CACHE MISS for hourly forecast at {lat}, {lon}. Fetching live data...")
    live = fetch_hourly_forecast(lat, lon)
    if not live: raise HTTPException(status_code=500, detail="Could not retrieve hourly forecast.")
    save_hourly_forecast_to_db(lat, lon, live)
    return live

@app.get("/forecast")
def get_daily_forecast(lat: float, lon: float):
    cached = get_forecast_from_db(lat, lon)
    if cached and len(cached) >= 5:
        print(f"CACHE HIT for 5-day forecast at {lat}, {lon}")
        return [{"date": r[0], "max_temp": r[1], "min_temp": r[2], "weather_code": r[3], "sunrise": r[4], "sunset": r[5], "precipitation_sum": r[6], "precipitation_probability_max": r[7]} for r in cached]
    print(f"CACHE MISS for 5-day forecast at {lat}, {lon}. Fetching live data...")
    live = fetch_daily_forecast(lat, lon)
    if not live: raise HTTPException(status_code=500, detail="Could not retrieve live forecast data.")
    save_forecast_to_db(lat, lon, live)
    return live

@app.get("/aqi-alerts")
def get_aqi_and_alerts(lat: float, lon: float):
    # Caching is not implemented for this endpoint in the prototype
    print(f"Fetching AQI & Alerts data for {lat}, {lon}...")
    data = fetch_aqi_and_alerts(lat, lon)
    if not data["aqi"]:
        raise HTTPException(status_code=500, detail="Could not retrieve Air Quality data.")
    return data

# --- Mount the Static Files (Frontend) ---
app.mount("/", StaticFiles(directory="static", html=True), name="static")
