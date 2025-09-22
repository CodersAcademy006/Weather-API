# Save this file as "app.py"
import psycopg2
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from datetime import datetime, timedelta, timezone
import auth # Import the entire auth module

# --- Configuration & Initialization ---
DB_CONNECTION_STRING = "postgresql://postgres.kucoxmriguvqulnkzpcw:S.La9c4vc#wE2gq@aws-1-ap-south-1.pooler.supabase.com:6543/postgres"
GOOGLE_CLIENT_ID = "907619015371-uok8j31a979f7ii4t1094csjf7ij9qqk.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"
GOOGLE_REDIRECT_URI = "http://127.0.0.1:3000/weather-api/google-callback.html" # Assumes frontend runs on port 3000

app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

config = Config(environ={"GOOGLE_CLIENT_ID": GOOGLE_CLIENT_ID, "GOOGLE_CLIENT_SECRET": GOOGLE_CLIENT_SECRET})
oauth = OAuth(config)
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# --- Pydantic Models ---
class UserCreate(BaseModel):
    email: str
    password: str

class GoogleAuthCode(BaseModel):
    code: str

# --- Database Helper Functions ---
def get_user_from_db(email: str):
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cursor = conn.cursor()
    cursor.execute("SELECT email, hashed_password, auth_provider FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return {"email": user[0], "hashed_password": user[1], "auth_provider": user[2]}
    return None

def create_user_in_db(email, password=None, provider='email'):
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cursor = conn.cursor()
    hashed_password = auth.get_password_hash(password) if password else None
    cursor.execute("INSERT INTO users (email, hashed_password, auth_provider) VALUES (%s, %s, %s)", (email, hashed_password, provider))
    conn.commit()
    conn.close()

# ====================================================================
#  AUTHENTICATION ENDPOINTS
# ====================================================================

@app.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(user: UserCreate):
    if get_user_from_db(user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    create_user_in_db(user.email, password=user.password, provider='email')
    return {"email": user.email, "message": "User created successfully"}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user_from_db(form_data.username)
    if not user or not user["hashed_password"] or not auth.verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token = auth.create_access_token(data={"sub": user["email"]})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/google/exchange")
async def auth_via_google_exchange(auth_code: GoogleAuthCode):
    try:
        token = await oauth.google.authorize_access_token(code=auth_code.code, redirect_uri=GOOGLE_REDIRECT_URI)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Could not authorize Google token: {e}")
    
    user_info = token.get('userinfo')
    if not user_info or not user_info.get('email'):
        raise HTTPException(status_code=400, detail="Could not retrieve user info from Google")
    
    email = user_info['email']
    if not get_user_from_db(email):
        create_user_in_db(email, provider='google')
        
    access_token = auth.create_access_token(data={"sub": email})
    return {"access_token": access_token, "token_type": "bearer"}

# ====================================================================
#  PROTECTED WEATHER ENDPOINTS
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
    insert_query = "INSERT INTO weather_readings (location_name, latitude, longitude, timestamp, temperature_c, humidity_pct, pressure_hpa, wind_speed_mps, precip_mm, weather_code, apparent_temperature, uv_index) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (location_name, timestamp) DO NOTHING;"
    for row in data_rows:
        values = (row['location_name'], row['latitude'], row['longitude'], row['timestamp'], row['temperature_c'], row['humidity_pct'], row['pressure_hpa'], row['wind_speed_mps'], row['precip_mm'], row['weather_code'], row['apparent_temperature'], row['uv_index'])
        cursor.execute(insert_query, values)
    conn.commit()
    conn.close()

def fetch_live_weather(lat, lon):
    api_url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": lat, "longitude": lon, "current": "temperature_2m,apparent_temperature,precipitation,weather_code,relative_humidity_2m,wind_speed_10m,uv_index,pressure_msl", "timezone": "auto"}
    response = requests.get(api_url, params=params)
    if response.status_code != 200: return None
    raw = response.json()['current']
    return { "location_name": f"Lat_{lat}_Lon_{lon}", "latitude": lat, "longitude": lon, "timestamp": datetime.fromisoformat(raw['time']), "temperature_c": raw['temperature_2m'], "humidity_pct": raw['relative_humidity_2m'], "pressure_hpa": raw['pressure_msl'], "wind_speed_mps": round(raw['wind_speed_10m'] / 3.6, 2), "precip_mm": raw['precipitation'], "weather_code": raw['weather_code'], "apparent_temperature": raw['apparent_temperature'], "uv_index": raw['uv_index'] }

@app.get("/weather")
def get_weather(lat: float, lon: float, user: dict = Depends(auth.get_current_user)):
    cached = get_weather_from_db(lat, lon)
    if cached: return {"source": "cache", "timestamp": cached[4], "temperature_c": cached[5], "humidity_pct": cached[6], "pressure_hpa": cached[7], "wind_speed_mps": cached[8], "precip_mm": cached[9], "apparent_temperature": cached[10], "uv_index": cached[11]}
    live = fetch_live_weather(lat, lon)
    if not live: raise HTTPException(status_code=500, detail="Could not retrieve live weather data.")
    save_weather_to_db([live])
    return {"source": "live", **live}

# --- HOURLY FORECAST ---
def get_hourly_forecast_from_db(lat, lon):
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cursor = conn.cursor()
    six_hours_ago = datetime.now(timezone.utc) - timedelta(hours=6)
    query = "SELECT forecast_time, temperature_c, precipitation_prob, wind_speed_mps FROM hourly_forecasts WHERE latitude = %s AND longitude = %s AND created_at >= %s ORDER BY forecast_time ASC LIMIT 24;"
    cursor.execute(query, (lat, lon, six_hours_ago))
    results = cursor.fetchall()
    conn.close()
    return results

def save_hourly_forecast_to_db(lat, lon, forecast_data):
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cursor = conn.cursor()
    query = "INSERT INTO hourly_forecasts (latitude, longitude, forecast_time, temperature_c, precipitation_prob, wind_speed_mps) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (latitude, longitude, forecast_time) DO UPDATE SET temperature_c = EXCLUDED.temperature_c, precipitation_prob = EXCLUDED.precipitation_prob, wind_speed_mps = EXCLUDED.wind_speed_mps, created_at = NOW();"
    for hour in forecast_data:
        cursor.execute(query, (lat, lon, hour['time'], hour['temp'], hour['precip_prob'], hour['wind']))
    conn.commit()
    conn.close()

def fetch_hourly_forecast(lat, lon):
    api_url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": lat, "longitude": lon, "hourly": "temperature_2m,precipitation_probability,wind_speed_10m", "forecast_days": 1, "timezone": "auto"}
    response = requests.get(api_url, params=params)
    if response.status_code != 200: return None
    raw = response.json()['hourly']
    return [{"time": raw['time'][i], "temp": raw['temperature_2m'][i], "precip_prob": raw['precipitation_probability'][i], "wind": round(raw['wind_speed_10m'][i] / 3.6, 2)} for i in range(len(raw['time']))]

@app.get("/hourly")
def get_hourly_forecast(lat: float, lon: float, user: dict = Depends(auth.get_current_user)):
    cached = get_hourly_forecast_from_db(lat, lon)
    if cached and len(cached) >= 24: return [{"time": r[0], "temp": r[1], "precip_prob": r[2], "wind": r[3]} for r in cached]
    live = fetch_hourly_forecast(lat, lon)
    if not live: raise HTTPException(status_code=500, detail="Could not retrieve hourly forecast.")
    save_hourly_forecast_to_db(lat, lon, live)
    return live

# --- DAILY FORECAST ---
def get_forecast_from_db(lat, lon):
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cursor = conn.cursor()
    six_hours_ago = datetime.now(timezone.utc) - timedelta(hours=6)
    query = "SELECT forecast_date, max_temp_c, min_temp_c, weather_code FROM daily_forecasts WHERE latitude = %s AND longitude = %s AND created_at >= %s ORDER BY forecast_date ASC;"
    cursor.execute(query, (lat, lon, six_hours_ago))
    results = cursor.fetchall()
    conn.close()
    return results

def save_forecast_to_db(lat, lon, forecast_data):
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cursor = conn.cursor()
    query = "INSERT INTO daily_forecasts (latitude, longitude, forecast_date, max_temp_c, min_temp_c, weather_code) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (latitude, longitude, forecast_date) DO UPDATE SET max_temp_c = EXCLUDED.max_temp_c, min_temp_c = EXCLUDED.min_temp_c, weather_code = EXCLUDED.weather_code, created_at = NOW();"
    for day in forecast_data:
        cursor.execute(query, (lat, lon, day['date'], day['max_temp'], day['min_temp'], day['weather_code']))
    conn.commit()
    conn.close()

def fetch_daily_forecast(lat, lon):
    api_url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": lat, "longitude": lon, "daily": "weather_code,temperature_2m_max,temperature_2m_min", "forecast_days": 5, "timezone": "auto"}
    response = requests.get(api_url, params=params)
    if response.status_code != 200: return None
    raw = response.json()['daily']
    return [{"date": raw['time'][i], "max_temp": raw['temperature_2m_max'][i], "min_temp": raw['temperature_2m_min'][i], "weather_code": raw['weather_code'][i]} for i in range(len(raw['time']))]

@app.get("/forecast")
def get_5_day_forecast(lat: float, lon: float, user: dict = Depends(auth.get_current_user)):
    cached = get_forecast_from_db(lat, lon)
    if cached and len(cached) >= 5: return [{"date": r[0], "max_temp": r[1], "min_temp": r[2], "weather_code": r[3]} for r in cached]
    live = fetch_daily_forecast(lat, lon)
    if not live: raise HTTPException(status_code=500, detail="Could not retrieve live forecast data.")
    save_forecast_to_db(lat, lon, live)
    return live