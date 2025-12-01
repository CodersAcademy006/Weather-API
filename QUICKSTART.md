# 🚀 Quick Start Guide - IntelliWeather API v3.0.0

## Phase 3: LEVEL 1 Enterprise Features

Welcome to IntelliWeather v3.0! This guide will help you get started with the new enterprise-grade features.

---

## ⚡ Quick Installation

### Option 1: Local Development

```bash
# 1. Clone and navigate to project
cd /workspaces/Weather-API

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment (optional)
cp .env.example .env
# Edit .env if you have API keys

# 4. Start the server
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Option 2: Docker

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

---

## 🎯 Test the New Features

### 1. Nowcast (High-Resolution 2-Hour Forecast)

```bash
# Get 15-minute interval forecast for New York
curl "http://localhost:8000/api/v3/forecast/nowcast?latitude=40.7128&longitude=-74.0060" | jq

# Response includes:
# - 15-minute intervals for next 2 hours
# - Temperature, precipitation, wind
# - Weather codes
```

### 2. Extended Hourly Forecast (7 Days)

```bash
# Get 48-hour forecast
curl "http://localhost:8000/api/v3/forecast/hourly?latitude=40.7128&longitude=-74.0060&hours=48" | jq

# Get 7-day hourly with hybrid data
curl "http://localhost:8000/api/v3/forecast/hourly?latitude=40.7128&longitude=-74.0060&hours=168&hybrid=true" | jq
```

### 3. Extended Daily Forecast (16 Days)

```bash
# Get 16-day forecast
curl "http://localhost:8000/api/v3/forecast/daily?latitude=40.7128&longitude=-74.0060&days=16" | jq
```

### 4. Complete Forecast Package

```bash
# All-in-one: Nowcast + Hourly + Daily
curl "http://localhost:8000/api/v3/forecast/complete?latitude=40.7128&longitude=-74.0060" | jq
```

### 5. Weather Insights

```bash
# Get all calculated insights
curl "http://localhost:8000/api/v3/insights/current?latitude=40.7128&longitude=-74.0060" | jq

# Specific insights
curl "http://localhost:8000/api/v3/insights/fire-risk?latitude=34.0522&longitude=-118.2437&days_since_rain=7" | jq
curl "http://localhost:8000/api/v3/insights/uv-exposure?latitude=25.7617&longitude=-80.1918" | jq
curl "http://localhost:8000/api/v3/insights/travel-disruption?latitude=51.5074&longitude=-0.1278" | jq
curl "http://localhost:8000/api/v3/insights/comfort?latitude=28.6139&longitude=77.2090" | jq
curl "http://localhost:8000/api/v3/insights/feels-like?latitude=35.6762&longitude=139.6503" | jq
```

### 6. Enhanced Geocoding

```bash
# Autocomplete search
curl "http://localhost:8000/geocode/autocomplete?q=New%20Yo&limit=5" | jq

# Popular locations
curl "http://localhost:8000/geocode/popular?limit=20" | jq

# Nearby cities (within 100km)
curl "http://localhost:8000/geocode/nearby?lat=40.7128&lon=-74.0060&radius_km=100&limit=10" | jq
```

---

## 🌐 Access API Documentation

Once the server is running:

**Interactive API Explorer:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Metrics:**
```bash
curl http://localhost:8000/metrics
```

---

## 🔑 API Keys (Optional)

If you want to use API key authentication:

1. **Create an account:**
```bash
curl -X POST "http://localhost:8000/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your@email.com",
    "password": "securepassword",
    "full_name": "Your Name"
  }'
```

2. **Login:**
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your@email.com",
    "password": "securepassword"
  }' \
  -c cookies.txt
```

3. **Create API key:**
```bash
curl -X POST "http://localhost:8000/apikeys" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "name": "My App Key",
    "rate_limit_per_minute": 100
  }'
```

4. **Use API key:**
```bash
curl "http://localhost:8000/api/v3/forecast/nowcast?latitude=40.7128&longitude=-74.0060" \
  -H "X-API-Key: your-api-key-here"
```

---

## 📊 Example Use Cases

### Use Case 1: Fire Risk Assessment (Wildfire Monitoring)

```bash
#!/bin/bash
# Monitor fire risk for California

LOCATIONS=(
  "34.0522,-118.2437,Los Angeles"
  "37.7749,-122.4194,San Francisco"
  "32.7157,-117.1611,San Diego"
)

for loc in "${LOCATIONS[@]}"; do
  IFS=',' read -r lat lon name <<< "$loc"
  echo "=== Fire Risk for $name ==="
  
  curl -s "http://localhost:8000/api/v3/insights/fire-risk?latitude=$lat&longitude=$lon&days_since_rain=10" \
    | jq '{
        location: "'$name'",
        score: .fire_risk.score,
        category: .fire_risk.category,
        recommendation: .fire_risk.recommendation
      }'
  echo ""
done
```

### Use Case 2: Event Planning Dashboard

```bash
#!/bin/bash
# Check conditions for outdoor event

LAT=40.7128
LON=-74.0060

echo "=== Event Weather Assessment ==="

# Get complete forecast
echo "1. Complete Forecast:"
curl -s "http://localhost:8000/api/v3/forecast/complete?latitude=$LAT&longitude=$LON" \
  | jq '{
      nowcast: .nowcast.time[0:4],
      hourly_temps: .hourly.temperature_2m[0:24],
      daily_summary: .daily.temperature_2m_max[0:3]
    }'

# Get comfort index
echo -e "\n2. Comfort Assessment:"
curl -s "http://localhost:8000/api/v3/insights/comfort?latitude=$LAT&longitude=$LON" \
  | jq '.comfort'

# Get UV exposure
echo -e "\n3. UV Risk:"
curl -s "http://localhost:8000/api/v3/insights/uv-exposure?latitude=$LAT&longitude=$LON" \
  | jq '.uv_exposure'

# Get travel conditions
echo -e "\n4. Travel Conditions:"
curl -s "http://localhost:8000/api/v3/insights/travel-disruption?latitude=$LAT&longitude=$LON" \
  | jq '.travel_disruption'
```

### Use Case 3: Location-Based App with Autocomplete

```python
import requests
import json

BASE_URL = "http://localhost:8000"

def search_and_forecast(query):
    """Search for location and get forecast."""
    
    # 1. Autocomplete search
    print(f"Searching for: {query}")
    autocomplete_resp = requests.get(
        f"{BASE_URL}/geocode/autocomplete",
        params={"q": query, "limit": 3}
    )
    suggestions = autocomplete_resp.json()["suggestions"]
    
    if not suggestions:
        print("No locations found")
        return
    
    # 2. Select first result
    location = suggestions[0]
    print(f"\nSelected: {location['display_name']}")
    print(f"Coordinates: {location['latitude']}, {location['longitude']}")
    
    # 3. Get complete forecast
    forecast_resp = requests.get(
        f"{BASE_URL}/api/v3/forecast/complete",
        params={
            "latitude": location['latitude'],
            "longitude": location['longitude']
        }
    )
    forecast = forecast_resp.json()
    
    # 4. Get insights
    insights_resp = requests.get(
        f"{BASE_URL}/api/v3/insights/current",
        params={
            "latitude": location['latitude'],
            "longitude": location['longitude']
        }
    )
    insights = insights_resp.json()
    
    # 5. Display results
    print("\n=== FORECAST SUMMARY ===")
    print(f"Timezone: {forecast['timezone']}")
    
    if forecast.get('nowcast'):
        print(f"\nNowcast (next 2 hours):")
        print(f"  Intervals: {len(forecast['nowcast'].get('time', []))}")
    
    if forecast.get('hourly'):
        temps = forecast['hourly'].get('temperature_2m', [])[:24]
        print(f"\n24-Hour Temps: {temps[0]:.1f}°C - {max(temps):.1f}°C")
    
    print("\n=== INSIGHTS ===")
    if 'insights' in insights and insights['insights']:
        for key, value in insights['insights'].items():
            print(f"{key}: {value}")

# Example usage
search_and_forecast("London")
```

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file:

```bash
# Application
APP_NAME=IntelliWeather
APP_VERSION=3.0.0
DEBUG=false

# External APIs
WEATHERAPI_KEY=your_weatherapi_key_here
ENABLE_FALLBACK=true

# Caching
CACHE_TTL_SECONDS=3600
CACHE_MAX_SIZE=1000

# Rate Limiting
RATE_LIMIT_PER_MIN=60

# Popular Locations (customize for your region)
POPULAR_LOCATIONS=40.7128,-74.0060,New York;51.5074,-0.1278,London;35.6762,139.6503,Tokyo

# Phase 3 Features (all enabled by default)
FEATURE_NOWCAST=true
FEATURE_EXTENDED_HOURLY=true
FEATURE_EXTENDED_DAILY=true
FEATURE_HYBRID_FORECAST=true
FEATURE_HEAT_INDEX=true
FEATURE_FIRE_RISK=true
FEATURE_UV_EXPOSURE=true
FEATURE_TRAVEL_DISRUPTION=true
FEATURE_AUTOCOMPLETE=true
```

---

## 📈 Performance Tips

### 1. Leverage Caching
```bash
# First request (cache miss) - slower
time curl "http://localhost:8000/api/v3/forecast/hourly?latitude=40.7128&longitude=-74.0060"

# Second request (cache hit) - much faster!
time curl "http://localhost:8000/api/v3/forecast/hourly?latitude=40.7128&longitude=-74.0060"
```

### 2. Use Complete Endpoint for Multiple Data Points
```bash
# Instead of 3 separate calls:
# /nowcast + /hourly + /daily

# Use single call:
curl "http://localhost:8000/api/v3/forecast/complete?latitude=40.7128&longitude=-74.0060"
```

### 3. Monitor Cache Performance
```bash
# Check Prometheus metrics
curl http://localhost:8000/metrics | grep cache_hits
curl http://localhost:8000/metrics | grep cache_misses
```

---

## 🐛 Troubleshooting

### Issue: "Unable to fetch forecast data"
**Solution:** Check if Open-Meteo API is accessible:
```bash
curl "https://api.open-meteo.com/v1/forecast?latitude=40.7128&longitude=-74.0060&current=temperature_2m"
```

### Issue: "Geocoding service unavailable"
**Solution:** Verify geocoding API:
```bash
curl "https://geocoding-api.open-meteo.com/v1/search?name=London"
```

### Issue: Hybrid mode not working
**Solution:** Check WeatherAPI key in `.env`:
```bash
WEATHERAPI_KEY=your_valid_key_here
ENABLE_FALLBACK=true
```

### Issue: Slow response times
**Solution:** 
1. Check cache hit ratio in metrics
2. Increase `CACHE_MAX_SIZE` in config
3. Enable Redis for production caching

---

## 🚀 Next Steps

### For Developers:
1. Explore the full API at http://localhost:8000/docs
2. Read `PHASE3_README.md` for detailed documentation
3. Check `ARCHITECTURE.md` for system design
4. Review test files in `tests/`

### For Production:
1. Set up Redis for distributed caching
2. Configure PostgreSQL for persistent storage
3. Enable Sentry for error tracking
4. Set up Nginx reverse proxy
5. Deploy with Docker Compose or Kubernetes

### Build More Features:
1. Implement LEVEL 2 features (Pollen, Marine, Solar APIs)
2. Create developer SDKs (Python, JavaScript)
3. Add developer dashboard
4. Implement PostgreSQL migration

---

## 📚 Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **Phase 3 Features**: `PHASE3_README.md`
- **Architecture**: `ARCHITECTURE.md`
- **Changelog**: `CHANGELOG.md`
- **Roadmap**: `future_build.md`

---

## 💬 Support

Found a bug or have a question?
- Check the API docs first
- Review troubleshooting section
- Check existing issues in the repo

---

**Happy coding! 🎊**

Built with ❤️ for enterprise-grade weather intelligence
