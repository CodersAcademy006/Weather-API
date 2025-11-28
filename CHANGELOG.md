# Changelog

All notable changes to IntelliWeather API will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2024-01-15

### Added - Phase 2 Features

#### Weather Endpoints V2
- `GET /weather/hourly` - Hourly forecast (24/48/72 hours) with CSV export
- `GET /weather/daily` - Daily forecast (7/14 days) with CSV export
- `GET /weather/historical` - Historical weather data with date range validation
- Support for metric/imperial unit conversion
- Pydantic response models with OpenAPI examples

#### Geocoding
- `GET /geocode/search` - Location search by name with caching
- `GET /geocode/reverse` - Reverse geocoding (coordinates to location)
- Result normalization and deduplication
- 24-hour cache TTL for geocoding results

#### Weather Alerts
- `GET /alerts` - Active weather alerts for a location
- Alert generation based on weather conditions (thunderstorms, high winds, etc.)
- `POST /alerts/refresh` - Admin endpoint to refresh alerts cache
- 15-minute cache TTL for alerts

#### Downloadable Reports
- `GET /weather/download` - Download weather reports
- PDF report generation with temperature charts
- Excel report generation with formatted sheets
- Report caching for 30 minutes

#### API Key Management
- `POST /apikeys` - Create new API key
- `GET /apikeys` - List user's API keys
- `DELETE /apikeys/{key_id}` - Revoke API key
- Per-key rate limiting
- Secure key hashing (only prefix stored)

#### ML Predictions
- `GET /predict/nextday` - Next-day temperature prediction
- Simple linear regression model on historical data
- `GET /predict/model/info` - Model metadata
- `POST /predict/model/train` - Trigger model training

#### Internationalization (i18n)
- `GET /i18n/languages` - Supported languages
- `GET /i18n/translations` - All translations for a language
- `GET /i18n/translate` - Single key translation
- `GET /i18n/weather-description` - Localized weather descriptions
- Supported: English, Hindi, Urdu, Arabic, Spanish

#### Admin Dashboard
- `GET /admin/dashboard` - Admin dashboard HTML page
- `GET /admin/api/stats` - Dashboard statistics
- `GET /admin/api/health` - System health check
- `GET /admin/api/metrics` - Detailed metrics
- `POST /admin/api/cache/clear` - Clear application cache

### Changed
- Updated FastAPI app with OpenAPI tags for better documentation
- Feature flags for all Phase 2 features in config.py
- Enhanced error responses with proper HTTP status codes
- Improved OpenAPI documentation with examples

### Configuration
New environment variables:
- `FEATURE_WEATHER_V2` - Enable Weather V2 endpoints (default: true)
- `FEATURE_GEOCODING` - Enable geocoding endpoints (default: true)
- `FEATURE_ALERTS` - Enable alerts endpoints (default: true)
- `FEATURE_DOWNLOADS` - Enable download endpoints (default: true)
- `FEATURE_API_KEYS` - Enable API key management (default: true)
- `FEATURE_ML_PREDICTION` - Enable ML predictions (default: true)
- `FEATURE_ADMIN_DASHBOARD` - Enable admin dashboard (default: true)
- `FEATURE_I18N` - Enable internationalization (default: true)
- `GEOCODE_CACHE_TTL_SECONDS` - Geocoding cache TTL (default: 86400)
- `API_KEY_RATE_LIMIT_DEFAULT` - Default API key rate limit (default: 100)
- `ML_HISTORICAL_DAYS` - Historical days for ML training (default: 365)

---

## [1.0.0] - 2024-01-14

### Added - Phase 1 Features

#### Core Backend
- `config.py` - Centralized configuration with pydantic-settings
- `storage.py` - CSV-backed storage for users, sessions, search history
- `cache.py` - In-memory caching with TTL and background cleanup
- `logging_config.py` - Structured JSON logging

#### Authentication & Sessions
- `session_middleware.py` - Server-side sessions with UUID tokens
- `routes/auth.py` - Signup, login, logout endpoints
- Bcrypt password hashing
- Secure session cookies (httpOnly, SameSite)

#### Rate Limiting
- `middleware/rate_limiter.py` - Sliding window rate limiter
- Configurable requests per minute per IP
- 429 responses with Retry-After headers

#### Health & Metrics
- `/healthz` - Health check endpoint
- `/metrics` - Application metrics
- `/metrics/prometheus` - Prometheus format metrics

#### Weather Endpoints
- `GET /weather` - Current weather with caching
- `GET /hourly` - Hourly forecast
- `GET /forecast` - 7-day forecast
- `GET /aqi-alerts` - Air quality and alerts

#### UI
- Royal theme with glassmorphism design
- Animated starfield background
- Floating gradient orbs
- Aurora effect animation
- Crown decoration
- Dark purple (#4a1c6e) and gold (#d4af37) color scheme
- Playfair Display typography
- Responsive design

#### Docker & Deployment
- `Dockerfile` - Multi-stage build
- `docker-compose.yml` - Multi-container setup with scaling
- `nginx.conf` - Load balancer configuration

#### Documentation
- `README.md` - Comprehensive documentation
- `QA.md` - Testing checklist
- `demo_script.md` - Presentation guide

---

## [0.1.0] - Initial Release

### Added
- Basic FastAPI application
- Static file serving
- Open-Meteo API integration
