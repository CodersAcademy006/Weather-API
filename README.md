# 🌦️ IntelliWeather

A production-grade weather API built with FastAPI, featuring real-time weather data, intelligent caching, user authentication, rate limiting, and horizontal scaling support. Designed as a modern competitor to AccuWeather.

![Dashboard](https://github.com/user-attachments/assets/c1fc16fb-2290-4376-9c8c-2b109d03de41)

## ✨ Features

### Phase 1 - Core Features

#### Weather Data
- **Real-time Weather** - Current temperature, humidity, wind speed, UV index, and more
- **Hourly Forecasts** - 24-hour detailed weather predictions
- **7-Day Forecast** - Extended weather outlook with high/low temperatures
- **Air Quality Index** - AQI monitoring with health indicators

#### UI & UX
- **Royal Theme** - Premium purple and gold color scheme
- **Animated Backgrounds** - Starfield, floating orbs, aurora effects
- **Responsive Layout** - Works on mobile, tablet, and desktop
- **Connection Status** - Real-time backend connectivity indicator

#### Backend Features
- **Multi-tier Caching** - In-memory cache with configurable TTL
- **CSV Data Storage** - Simple file-based persistence
- **Session Authentication** - Secure server-side sessions
- **Rate Limiting** - Per-IP rate limiting
- **Health Checks** - `/healthz` endpoint for load balancers

### Phase 2 - Advanced Features

#### Enhanced Weather API
- **Hourly Endpoint V2** - 24/48/72 hour forecasts with CSV export
- **Daily Endpoint V2** - 7/14 day forecasts with CSV export
- **Historical Data** - Query weather data up to 1 year back
- **Unit Conversion** - Metric and imperial support

#### Geocoding
- **Location Search** - Search cities with autocomplete
- **Reverse Geocoding** - Get location from coordinates
- **Caching** - 24-hour cache for geocoding results

#### Weather Alerts
- **Active Alerts** - Get severe weather warnings
- **Alert Types** - Thunderstorms, high winds, precipitation, winter weather
- **Background Prefetch** - Automatic alert updates for popular locations

#### Downloadable Reports
- **PDF Reports** - Formatted weather reports with charts
- **Excel Reports** - Structured data with multiple sheets
- **Report Caching** - Generated reports are cached

#### ML Predictions
- **Next-Day Temperature** - Linear regression model
- **Confidence Intervals** - Prediction uncertainty
- **Model Training** - Periodic retraining on historical data

#### Multi-language Support
- **5 Languages** - English, Hindi, Urdu, Arabic, Spanish
- **UI Translations** - Full interface localization
- **Weather Descriptions** - Localized condition text

#### API Key Management
- **Personal API Keys** - Create keys for programmatic access
- **Per-Key Rate Limits** - Customizable limits per key
- **Usage Tracking** - Monitor API key usage

#### Admin Dashboard
- **Analytics** - User counts, cache stats, top locations
- **System Health** - Component status monitoring
- **Cache Management** - Clear cache from dashboard

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern async Python web framework
- **Pydantic** - Data validation with type hints
- **Uvicorn/Gunicorn** - ASGI server for production
- **Open-Meteo API** - Free weather data provider

### Frontend
- **HTML5/CSS3** - Royal theme design
- **Vanilla JavaScript** - No framework dependencies
- **Playfair Display** - Elegant typography

### Infrastructure
- **Docker** - Containerization
- **NGINX** - Load balancing & reverse proxy
- **Redis** (optional) - Session storage for scaled deployments

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- pip package manager
- Docker (optional, for containerized deployment)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/CodersAcademy006/Weather-API.git
   cd Weather-API
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the server**
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Open in browser**
   - Dashboard: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Scale to multiple replicas
docker-compose up -d --scale app=3

# View logs
docker-compose logs -f
```

## 📡 API Endpoints

### Phase 1 - Weather Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/weather?lat={lat}&lon={lon}` | GET | Current weather |
| `/hourly?lat={lat}&lon={lon}` | GET | 24-hour forecast |
| `/forecast?lat={lat}&lon={lon}` | GET | 7-day forecast |
| `/aqi-alerts?lat={lat}&lon={lon}` | GET | Air quality & alerts |

### Phase 2 - Enhanced Weather

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/weather/hourly?lat=&lon=&hours=` | GET | Hourly forecast (24/48/72h) |
| `/weather/daily?lat=&lon=&days=` | GET | Daily forecast (7/14 days) |
| `/weather/historical?lat=&lon=&start=&end=` | GET | Historical data |
| `/weather/download?lat=&lon=&type=pdf` | GET | Download report |

### Phase 2 - Geocoding

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/geocode/search?q={query}` | GET | Search locations |
| `/geocode/reverse?lat=&lon=` | GET | Reverse geocode |

### Phase 2 - Alerts & Prediction

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/alerts?lat=&lon=` | GET | Weather alerts |
| `/predict/nextday?lat=&lon=` | GET | Next-day prediction |

### Phase 2 - API Keys & i18n

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/apikeys` | POST | Create API key |
| `/apikeys` | GET | List API keys |
| `/apikeys/{id}` | DELETE | Revoke API key |
| `/i18n/translations?lang=` | GET | Get translations |

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/signup` | POST | Create account |
| `/auth/login` | POST | Login |
| `/auth/logout` | POST | Logout |
| `/auth/me` | GET | Get current user |

### Admin & System

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/admin/dashboard` | GET | Admin dashboard |
| `/admin/api/stats` | GET | Dashboard stats |
| `/healthz` | GET | Health check |
| `/metrics` | GET | Application metrics |

### Example Requests

```bash
# Current weather
curl "http://localhost:8000/weather?lat=40.7128&lon=-74.0060"

# Hourly forecast with CSV export
curl "http://localhost:8000/weather/hourly?lat=40.7128&lon=-74.0060&hours=48&format=csv" -o forecast.csv

# Search for a city
curl "http://localhost:8000/geocode/search?q=London&limit=5"

# Get weather alerts
curl "http://localhost:8000/alerts?lat=40.7128&lon=-74.0060"

# Next-day temperature prediction
curl "http://localhost:8000/predict/nextday?lat=40.7128&lon=-74.0060"

# Download PDF report
curl "http://localhost:8000/weather/download?lat=40.7128&lon=-74.0060&type=pdf" -o report.pdf

# Get Hindi translations
curl "http://localhost:8000/i18n/translations?lang=hi"
```

## 🏗️ Project Architecture

```
Weather-API/
├── app.py                     # Main FastAPI application
├── config.py                  # Centralized configuration
├── cache.py                   # In-memory caching system
├── storage.py                 # CSV-based data storage
├── session_middleware.py      # Session management
├── logging_config.py          # Structured logging
├── metrics.py                 # Health checks & metrics
├── middleware/
│   └── rate_limiter.py        # Rate limiting
├── routes/
│   ├── auth.py                # Authentication
│   ├── weather_v2.py          # Enhanced weather endpoints
│   ├── geocode.py             # Geocoding
│   ├── alerts.py              # Weather alerts
│   ├── downloads.py           # Report downloads
│   ├── apikeys.py             # API key management
│   ├── predict.py             # ML predictions
│   ├── admin.py               # Admin dashboard
│   └── i18n.py                # Internationalization
├── modules/
│   ├── geocode.py             # Geocoding service
│   ├── api_keys.py            # API key manager
│   ├── i18n.py                # Translation service
│   ├── prediction.py          # ML prediction service
│   └── reports/
│       ├── pdf_report.py      # PDF generation
│       └── xlsx_report.py     # Excel generation
├── schemas/
│   ├── weather.py             # Weather models
│   ├── geocode.py             # Geocoding models
│   ├── alerts.py              # Alert models
│   └── api_keys.py            # API key models
├── workers/
│   ├── alerts_prefetch.py     # Alert prefetcher
│   └── train_model.py         # Model trainer
├── static/                    # Frontend files
├── tests/                     # Unit tests
├── data/                      # CSV storage
├── Dockerfile                 # Docker image
├── docker-compose.yml         # Multi-container setup
├── nginx.conf                 # Load balancer
├── requirements.txt           # Dependencies
├── CHANGELOG.md               # Version history
├── QA.md                      # Phase 1 QA checklist
├── QA_PHASE2.md               # Phase 2 QA checklist
├── demo_script.md             # Phase 1 demo guide
└── demo_phase2.md             # Phase 2 demo guide
```

## ⚙️ Configuration

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | IntelliWeather | Application name |
| `APP_PORT` | 8000 | Server port |
| `CACHE_TTL_SECONDS` | 3600 | Cache expiration |
| `SESSION_TIMEOUT_SECONDS` | 86400 | Session expiration |
| `RATE_LIMIT_PER_MIN` | 60 | Requests per minute per IP |

### Phase 2 Feature Flags

| Variable | Default | Description |
|----------|---------|-------------|
| `FEATURE_WEATHER_V2` | true | Enable enhanced weather |
| `FEATURE_GEOCODING` | true | Enable geocoding |
| `FEATURE_ALERTS` | true | Enable alerts |
| `FEATURE_DOWNLOADS` | true | Enable downloads |
| `FEATURE_API_KEYS` | true | Enable API keys |
| `FEATURE_ML_PREDICTION` | true | Enable predictions |
| `FEATURE_ADMIN_DASHBOARD` | true | Enable admin |
| `FEATURE_I18N` | true | Enable i18n |

### Additional Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `GEOCODE_CACHE_TTL_SECONDS` | 86400 | Geocode cache (24h) |
| `API_KEY_RATE_LIMIT_DEFAULT` | 100 | Default key rate limit |
| `ML_HISTORICAL_DAYS` | 365 | Training data days |
| `DEFAULT_LANGUAGE` | en | Default language |

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run Phase 2 specific tests
pytest tests/test_phase2.py -v
```

## 🎨 Screenshots

| Dashboard | Login | Sign Up |
|-----------|-------|---------|
| ![Dashboard](https://github.com/user-attachments/assets/c1fc16fb-2290-4376-9c8c-2b109d03de41) | ![Login](https://github.com/user-attachments/assets/d89050fb-aa97-4dcc-ab96-a1883e3b7aac) | ![Sign Up](https://github.com/user-attachments/assets/82d424be-c220-4c11-80cb-fa42eeb34fd6) |

## 🌐 Data Sources

- **Weather Data**: [Open-Meteo](https://open-meteo.com/)
- **Historical Weather**: [Open-Meteo Archive](https://open-meteo.com/en/docs/historical-weather-api)
- **Air Quality**: [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api)
- **Geocoding**: [Open-Meteo Geocoding API](https://open-meteo.com/en/docs/geocoding-api)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📧 Contact

Created by [@CodersAcademy006](https://github.com/CodersAcademy006)

---

⭐ Star this repo if you find it helpful!
