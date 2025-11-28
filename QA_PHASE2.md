# Phase 2 QA Checklist

## Prerequisites
- [ ] Python 3.10+ installed
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Server running: `uvicorn app:app --reload`

---

## 1. Weather V2 Endpoints

### 1.1 Hourly Forecast
```bash
# Get 24-hour forecast (JSON)
curl "http://localhost:8000/weather/hourly?lat=40.7128&lon=-74.006&hours=24"

# Get 48-hour forecast with imperial units
curl "http://localhost:8000/weather/hourly?lat=40.7128&lon=-74.006&hours=48&units=imperial"

# Download as CSV
curl "http://localhost:8000/weather/hourly?lat=40.7128&lon=-74.006&format=csv" -o hourly.csv
```
- [ ] Returns hourly data points
- [ ] Units conversion works (metric/imperial)
- [ ] CSV download works
- [ ] Cache hit on second request

### 1.2 Daily Forecast
```bash
# Get 7-day forecast
curl "http://localhost:8000/weather/daily?lat=40.7128&lon=-74.006&days=7"

# Get 14-day forecast
curl "http://localhost:8000/weather/daily?lat=40.7128&lon=-74.006&days=14"
```
- [ ] Returns daily data with sunrise/sunset
- [ ] 14-day forecast works
- [ ] Weather codes included

### 1.3 Historical Data
```bash
# Get historical data
curl "http://localhost:8000/weather/historical?lat=40.7128&lon=-74.006&start=2024-01-01&end=2024-01-07"

# Invalid date range (>1 year)
curl "http://localhost:8000/weather/historical?lat=40.7128&lon=-74.006&start=2022-01-01&end=2024-01-01"
```
- [ ] Historical data returns
- [ ] Date validation works (rejects >365 days)
- [ ] Error for invalid date range

---

## 2. Geocoding

### 2.1 Location Search
```bash
# Search for a city
curl "http://localhost:8000/geocode/search?q=London&limit=5"

# Search with language
curl "http://localhost:8000/geocode/search?q=Tokyo&lang=en"
```
- [ ] Returns location results with coordinates
- [ ] Includes country, timezone, population
- [ ] Cache hit on repeat search

### 2.2 Reverse Geocoding
```bash
# Reverse geocode coordinates
curl "http://localhost:8000/geocode/reverse?lat=51.5074&lon=-0.1278"
```
- [ ] Returns location info for coordinates
- [ ] Includes timezone

---

## 3. Weather Alerts

### 3.1 Get Alerts
```bash
# Get alerts for location
curl "http://localhost:8000/alerts?lat=40.7128&lon=-74.006"
```
- [ ] Returns alerts array (may be empty if no severe weather)
- [ ] Includes alert severity and descriptions
- [ ] Cache works (15-minute TTL)

### 3.2 Admin Refresh (requires auth)
```bash
# Refresh alerts (needs session cookie)
curl -X POST "http://localhost:8000/alerts/refresh" -b "session_id=YOUR_SESSION"
```
- [ ] Requires authentication
- [ ] Returns refresh count

---

## 4. Downloads

### 4.1 PDF Report
```bash
# Download PDF report
curl "http://localhost:8000/weather/download?lat=40.7128&lon=-74.006&type=pdf&range=daily&days=7" -o report.pdf
```
- [ ] PDF file downloads
- [ ] Contains weather data
- [ ] Report is cached

### 4.2 Excel Report
```bash
# Download Excel report
curl "http://localhost:8000/weather/download?lat=40.7128&lon=-74.006&type=excel&range=daily&days=7" -o report.xlsx
```
- [ ] Excel file downloads
- [ ] Contains formatted data
- [ ] Multiple sheets (Weather, Metadata)

---

## 5. API Keys

### 5.1 Create API Key
```bash
# First, login to get session
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass"}' \
  -c cookies.txt

# Create API key
curl -X POST "http://localhost:8000/apikeys" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Key","rate_limit":100}' \
  -b cookies.txt
```
- [ ] Returns API key (only shown once)
- [ ] Key has prefix `iw_live_`

### 5.2 List Keys
```bash
curl "http://localhost:8000/apikeys" -b cookies.txt
```
- [ ] Returns list of user's keys
- [ ] Shows usage statistics

### 5.3 Use API Key
```bash
# Use key in header
curl "http://localhost:8000/weather/hourly?lat=40.7128&lon=-74.006" \
  -H "X-API-Key: iw_live_YOUR_KEY"

# Use key in query param
curl "http://localhost:8000/weather/hourly?lat=40.7128&lon=-74.006&apikey=iw_live_YOUR_KEY"
```
- [ ] API key authentication works
- [ ] Rate limiting enforced per key

---

## 6. ML Prediction

### 6.1 Get Prediction
```bash
curl "http://localhost:8000/predict/nextday?lat=40.7128&lon=-74.006"
```
- [ ] Returns predicted temperature
- [ ] Includes confidence interval
- [ ] Shows model version

### 6.2 Model Info
```bash
curl "http://localhost:8000/predict/model/info"
```
- [ ] Returns model metadata
- [ ] Shows if model is trained

### 6.3 Train Model
```bash
curl -X POST "http://localhost:8000/predict/model/train?lat=40.7128&lon=-74.006"
```
- [ ] Model training completes
- [ ] Model saved to data/models/

---

## 7. Internationalization

### 7.1 Supported Languages
```bash
curl "http://localhost:8000/i18n/languages"
```
- [ ] Returns list: en, hi, ur, ar, es

### 7.2 Get Translations
```bash
# English
curl "http://localhost:8000/i18n/translations?lang=en"

# Hindi
curl "http://localhost:8000/i18n/translations?lang=hi"

# Arabic
curl "http://localhost:8000/i18n/translations?lang=ar"
```
- [ ] Returns translations for each language
- [ ] Hindi text is correct
- [ ] Arabic text is right-to-left

### 7.3 Weather Description
```bash
curl "http://localhost:8000/i18n/weather-description?code=3&lang=es"
```
- [ ] Returns localized weather description

---

## 8. Admin Dashboard

### 8.1 Dashboard Page
```bash
# Open in browser (requires admin login)
open http://localhost:8000/admin/dashboard
```
- [ ] Dashboard renders
- [ ] Shows statistics
- [ ] Shows system health

### 8.2 API Stats
```bash
curl "http://localhost:8000/admin/api/stats" -b cookies.txt
```
- [ ] Returns dashboard statistics
- [ ] Requires admin auth

### 8.3 System Health
```bash
curl "http://localhost:8000/admin/api/health" -b cookies.txt
```
- [ ] Shows storage status
- [ ] Shows cache status
- [ ] Shows API connectivity

---

## 9. Integration Tests

### 9.1 Full User Flow
1. [ ] Sign up new user
2. [ ] Login
3. [ ] Create API key
4. [ ] Use API key to fetch weather
5. [ ] Download report
6. [ ] Get prediction
7. [ ] Logout

### 9.2 Cache Verification
1. [ ] Make request (cache miss)
2. [ ] Make same request (cache hit)
3. [ ] Clear cache (admin)
4. [ ] Make request (cache miss again)

### 9.3 Rate Limiting
1. [ ] Create API key with rate_limit=5
2. [ ] Make 5 requests
3. [ ] 6th request returns 429

---

## 10. Performance Checks

- [ ] Response times < 500ms for cached requests
- [ ] Response times < 2s for live API requests
- [ ] Memory usage stable under load
- [ ] No memory leaks in cache cleanup

---

## Sign-off

| Tester | Date | Status |
|--------|------|--------|
|        |      |        |
