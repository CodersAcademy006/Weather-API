# 🌦️ IntelliWeather

A production-grade weather API built with FastAPI, featuring real-time weather data, intelligent caching, user authentication, rate limiting, and horizontal scaling support. Designed as a modern competitor to AccuWeather.

![Dashboard](https://github.com/user-attachments/assets/5a3e9289-f19e-4858-9eee-a82a04c9c0ad)

## ✨ Features

### Weather Data
- **Real-time Weather** - Current temperature, humidity, wind speed, UV index, and more
- **Hourly Forecasts** - 24-hour detailed weather predictions
- **7-Day Forecast** - Extended weather outlook with high/low temperatures
- **Air Quality Index** - AQI monitoring with health indicators

### UI & UX
- **Modern Glassmorphism Design** - Beautiful backdrop blur effects
- **Dynamic Themes** - Background changes based on weather (sunny, cloudy, rainy, snowy)
- **Responsive Layout** - Works on mobile, tablet, and desktop
- **Location Search** - Search for any city worldwide with autocomplete
- **Geolocation Support** - Automatic location detection
- **Connection Status** - Real-time backend connectivity indicator

### Backend Features
- **Multi-tier Caching** - In-memory cache with configurable TTL
- **CSV Data Storage** - Simple file-based persistence (upgradeable to PostgreSQL)
- **Session Authentication** - Secure server-side sessions with bcrypt
- **Rate Limiting** - Per-IP rate limiting with sliding window algorithm
- **Health Checks** - `/healthz` endpoint for load balancers
- **Metrics** - `/metrics` endpoint for observability
- **Structured Logging** - JSON-format logs for production

### DevOps
- **Docker Support** - Production-ready Dockerfile
- **Load Balancing** - NGINX reverse proxy configuration
- **Horizontal Scaling** - Scale with `docker-compose --scale app=N`

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern async Python web framework
- **Pydantic** - Data validation with type hints
- **Uvicorn/Gunicorn** - ASGI server for production
- **Open-Meteo API** - Free weather data provider

### Frontend
- **HTML5/CSS3** - Glassmorphism design
- **Vanilla JavaScript** - No framework dependencies
- **Inter Font** - Modern typography

### Infrastructure
- **Docker** - Containerization
- **NGINX** - Load balancing & reverse proxy
- **Redis** (optional) - Session storage for scaled deployments

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
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

### Weather Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/weather?lat={lat}&lon={lon}` | GET | Current weather |
| `/hourly?lat={lat}&lon={lon}` | GET | 24-hour forecast |
| `/forecast?lat={lat}&lon={lon}` | GET | 7-day forecast |
| `/aqi-alerts?lat={lat}&lon={lon}` | GET | Air quality & alerts |

### Authentication Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/signup` | POST | Create account |
| `/auth/login` | POST | Login |
| `/auth/logout` | POST | Logout |
| `/auth/me` | GET | Get current user |
| `/auth/session` | GET | Session info |

### System Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/healthz` | GET | Health check |
| `/metrics` | GET | Application metrics |
| `/metrics/prometheus` | GET | Prometheus format |
| `/api/info` | GET | API information |

### Example Request

```bash
curl "http://localhost:8000/weather?lat=40.7128&lon=-74.0060" | jq

# Response
{
  "source": "cache",
  "temperature_c": 22.5,
  "humidity_pct": 65,
  "wind_speed_mps": 3.5,
  "weather_code": 2,
  "apparent_temperature": 23.1,
  "uv_index": 5.2,
  "is_day": 1
}
```

## 🏗️ Project Architecture

```
Weather-API/
├── app.py                 # Main FastAPI application
├── config.py              # Centralized configuration
├── cache.py               # In-memory caching system
├── storage.py             # CSV-based data storage
├── session_middleware.py  # Session management
├── logging_config.py      # Structured logging
├── metrics.py             # Health checks & metrics
├── auth.py                # Legacy auth utilities
├── middleware/
│   ├── __init__.py
│   └── rate_limiter.py    # Rate limiting middleware
├── routes/
│   ├── __init__.py
│   └── auth.py            # Authentication routes
├── static/
│   ├── index.html         # Weather dashboard
│   ├── login.html         # Login page
│   ├── signup.html        # Signup page
│   └── google-callback.html
├── tests/
│   ├── __init__.py
│   └── test_modules.py    # Unit tests
├── data/                  # CSV storage directory
├── Dockerfile             # Docker image
├── docker-compose.yml     # Multi-container setup
├── nginx.conf             # Load balancer config
├── requirements.txt       # Python dependencies
├── QA.md                  # QA checklist
├── demo_script.md         # Presentation guide
└── README.md              # This file
```

## ⚙️ Configuration

All settings are configurable via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | IntelliWeather | Application name |
| `APP_PORT` | 8000 | Server port |
| `CACHE_TTL_SECONDS` | 3600 | Cache expiration (1 hour) |
| `SESSION_TIMEOUT_SECONDS` | 86400 | Session expiration (24 hours) |
| `RATE_LIMIT_PER_MIN` | 60 | Max requests per minute per IP |
| `LOG_LEVEL` | INFO | Logging level |
| `LOG_FORMAT` | json | Log format (json/text) |
| `SENTRY_DSN` | - | Sentry error tracking URL |

## 🔧 System Design Features

### Caching Strategy
```
Request → In-Memory Cache → Database Cache → External API
              ↓ (hit)           ↓ (hit)          ↓
           Response          Response       Save to cache
```

### Rate Limiting
- Sliding window algorithm
- 60 requests/minute per IP (configurable)
- Returns `429 Too Many Requests` with `Retry-After` header

### Session Management
- Server-side sessions with UUID tokens
- CSV-based storage (Redis-ready for production)
- Secure cookies (httpOnly, SameSite=Lax)

### Horizontal Scaling

> ⚠️ **Note**: CSV-based session storage does not work across multiple replicas. For production scaling, enable Redis session backend:

```yaml
# docker-compose.yml
environment:
  - SESSION_BACKEND=redis
  - REDIS_URL=redis://redis:6379/0
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test
pytest tests/test_modules.py::TestCache -v
```

## 🎨 Screenshots

| Login | Sign Up |
|-------|---------|
| ![Login](https://github.com/user-attachments/assets/d89050fb-aa97-4dcc-ab96-a1883e3b7aac) | ![Sign Up](https://github.com/user-attachments/assets/82d424be-c220-4c11-80cb-fa42eeb34fd6) |

## 🌐 Data Sources

- **Weather Data**: [Open-Meteo](https://open-meteo.com/)
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
