# Phase 2 Demo Script

## Demo Duration: 7-10 minutes

This script guides you through demonstrating the Phase 2 features of IntelliWeather API.

---

## Setup (Before Demo)

```bash
# Start the server
cd Weather-API
pip install -r requirements.txt
uvicorn app:app --reload --port 8000

# Open Swagger docs
open http://localhost:8000/docs
```

---

## Part 1: Weather V2 Endpoints (2 min)

### Show Enhanced Weather API

1. **Open Swagger UI** at `http://localhost:8000/docs`
   - Point out the organized tags: Weather V2, Geocoding, Alerts, etc.

2. **Hourly Forecast**
   ```bash
   curl "http://localhost:8000/weather/hourly?lat=40.7128&lon=-74.006&hours=48"
   ```
   - Show the structured JSON response
   - Highlight: temperature, humidity, precipitation probability

3. **CSV Export**
   ```bash
   curl "http://localhost:8000/weather/hourly?lat=40.7128&lon=-74.006&format=csv" -o hourly.csv
   open hourly.csv
   ```
   - "Users can export data to CSV for their own analysis"

4. **Historical Data**
   ```bash
   curl "http://localhost:8000/weather/historical?lat=40.7128&lon=-74.006&start=2024-01-01&end=2024-01-07"
   ```
   - "We can fetch historical weather for any date range up to 1 year"

---

## Part 2: Geocoding & Search (1 min)

### Location Search

1. **Search for a city**
   ```bash
   curl "http://localhost:8000/geocode/search?q=Lahore&limit=3"
   ```
   - Show coordinates, country, timezone, population

2. **Reverse Geocoding**
   ```bash
   curl "http://localhost:8000/geocode/reverse?lat=31.5204&lon=74.3587"
   ```
   - "From coordinates, we can get the location name"

3. **Show Cache Hit**
   - Make the same request again
   - Point out `"source": "cache"` in response
   - "Second request is instant - served from cache"

---

## Part 3: Weather Alerts (1 min)

### Alert System

1. **Get Alerts**
   ```bash
   curl "http://localhost:8000/alerts?lat=40.7128&lon=-74.006"
   ```
   - Show alert structure: severity, headline, instructions

2. **Explain the System**
   - "Alerts are generated based on weather conditions"
   - "In production, this would integrate with National Weather Service"
   - "Alerts are cached for 15 minutes"

---

## Part 4: Downloadable Reports (1.5 min)

### PDF and Excel Reports

1. **Download PDF Report**
   ```bash
   curl "http://localhost:8000/weather/download?lat=40.7128&lon=-74.006&type=pdf&range=daily&days=7" -o report.pdf
   open report.pdf
   ```
   - Show the formatted report with temperature chart

2. **Download Excel Report**
   ```bash
   curl "http://localhost:8000/weather/download?lat=40.7128&lon=-74.006&type=excel&range=daily&days=7" -o report.xlsx
   open report.xlsx
   ```
   - Show multiple sheets: Weather data, Metadata
   - "Excel files have proper styling and formatting"

---

## Part 5: ML Prediction (1 min)

### Temperature Prediction

1. **Get Next-Day Prediction**
   ```bash
   curl "http://localhost:8000/predict/nextday?lat=40.7128&lon=-74.006"
   ```
   - Show predicted temperature and confidence interval
   - "Simple ML model using historical data"

2. **Model Info**
   ```bash
   curl "http://localhost:8000/predict/model/info"
   ```
   - Show model version and training date

---

## Part 6: Multi-Language Support (1 min)

### Internationalization

1. **Show Supported Languages**
   ```bash
   curl "http://localhost:8000/i18n/languages"
   ```
   - List: English, Hindi, Urdu, Arabic, Spanish

2. **Get Hindi Translations**
   ```bash
   curl "http://localhost:8000/i18n/translations?lang=hi" | jq '.translations | {current_weather, feels_like, humidity}'
   ```
   - Show Hindi text

3. **Weather Description in Arabic**
   ```bash
   curl "http://localhost:8000/i18n/weather-description?code=3&lang=ar"
   ```
   - Show Arabic translation

---

## Part 7: API Key System (1 min)

### API Key Management

1. **Login First**
   ```bash
   curl -X POST "http://localhost:8000/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email":"demo@example.com","password":"demo123"}' \
     -c cookies.txt
   ```

2. **Create API Key**
   ```bash
   curl -X POST "http://localhost:8000/apikeys" \
     -H "Content-Type: application/json" \
     -d '{"name":"Demo Key","rate_limit":100}' \
     -b cookies.txt
   ```
   - "Key is only shown once - store securely"

3. **Use API Key**
   ```bash
   curl "http://localhost:8000/weather/hourly?lat=40.7128&lon=-74.006" \
     -H "X-API-Key: YOUR_API_KEY"
   ```
   - "Each key has its own rate limit"

---

## Part 8: Admin Dashboard (1 min)

### Analytics Dashboard

1. **Open Dashboard**
   - Navigate to `http://localhost:8000/admin/dashboard`
   - (Requires admin user)

2. **Show Statistics**
   - Total users
   - Active sessions
   - Cache hit rate
   - Top searched locations

3. **System Health**
   - Storage status
   - Cache operational
   - API connectivity

---

## Part 9: Scaling Demo (Optional, 1 min)

### Docker Scaling

```bash
# Show docker-compose
cat docker-compose.yml

# Scale to 3 instances
docker-compose up -d --scale app=3

# Show NGINX load balancing
curl http://localhost/weather?lat=40.7128&lon=-74.006
```

---

## Closing Points

1. **Architecture Highlights**
   - Multi-tier caching (memory → CSV → external API)
   - Feature flags for all Phase 2 features
   - Structured JSON logging
   - Thread-safe operations

2. **Production Ready**
   - Docker support with load balancing
   - Health checks and metrics
   - Rate limiting per IP and per API key
   - Secure session management

3. **Documentation**
   - Swagger/OpenAPI docs
   - README.md
   - QA checklist
   - Demo scripts

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Server won't start | Check `pip install -r requirements.txt` |
| 401 errors | Login first or provide API key |
| 429 errors | Rate limit hit, wait 60 seconds |
| Empty alerts | No severe weather at that location |
| PDF not rendering | Check if data fetched successfully |

---

## Q&A Preparation

**Q: Why CSV storage instead of a database?**
A: Simpler setup, no external dependencies. Demonstrates file-based persistence. Production would use PostgreSQL/Redis.

**Q: How does the ML model work?**
A: Linear regression on historical temperatures. Features: day of year (cyclical), previous temps, trend.

**Q: How accurate are predictions?**
A: Simple model with ±3°C confidence. Production would use more sophisticated approaches.

**Q: What happens if Open-Meteo is down?**
A: Cached data is returned if available. Error responses include 503 status with clear message.
