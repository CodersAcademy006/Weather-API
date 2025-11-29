# Changelog

All notable changes to IntelliWeather API will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.1] - 2024-11-29

### Fixed - Main Branch Compatibility

#### Backend Compatibility
- **SQLite Integration**: Merged SQLite database functions from main branch for seamless compatibility
- **Graceful Fallbacks**: All Phase 2/3 modules now load conditionally with graceful fallbacks
- **Error Handling**: Improved try/catch blocks for all module imports to prevent crashes
- **Database Initialization**: Combined SQLite init with CSV storage initialization

#### Frontend Fixes
- **Theme Manager**: Added null checks for `window.themeManager` to prevent undefined errors
- **Script Loading**: Fixed race condition in theme initialization

#### Documentation
- Updated CHANGELOG with compatibility fixes
- Confirmed all 27 tests pass

### Changed
- `app.py` now integrates SQLite (main branch) with in-memory caching (Phase 2) seamlessly
- Server startup message matches main branch output for consistency

## [3.0.0] - 2024-01-16

### Added - Phase 3 Features

#### Professional UI Redesign
- **New Header**: Fixed navigation bar with logo, nav links, theme toggle, and auth buttons
- **New Footer**: Full footer with branding, social links, product/resource/company columns
- **Dark/Light Mode**: System-aware theme with smooth transitions and localStorage persistence
- **Advanced Animations**: Hardware-accelerated animations using CSS transforms and opacity
- **Motion Controller**: JavaScript animation sequencing system with cancellation support
- **Skeleton Loaders**: Shimmer loading states during data fetches
- **Reduced Motion Support**: Respects `prefers-reduced-motion` system preference

#### Animation System
- `static/css/animations.css` - Comprehensive animation library
- `static/css/theme.css` - Theme system with CSS custom properties
- `static/js/motion.js` - MotionController for coordinated animations
- `static/js/theme.js` - ThemeManager for dark/light mode
- `static/js/search.js` - Enhanced search with autosuggest and keyboard navigation
- Design tokens for consistent timing (durations, easings, staggers)

#### Kubernetes Deployment
- `k8s/deployment.yaml` - Deployment, Service, Ingress, HPA, PVC, PDB manifests
- `k8s/secrets-template.yaml` - Secrets template (never commit actual secrets!)
- `k8s/local/local-setup.sh` - Script for local kind/minikube development
- Resource limits and requests for production stability
- Health probes (liveness, readiness)
- HorizontalPodAutoscaler for auto-scaling

#### Helm Chart
- `helm/intelliweather/Chart.yaml` - Chart metadata
- `helm/intelliweather/values.yaml` - Configurable values
- Redis and PostgreSQL as optional dependencies
- Support for custom annotations, resources, and environment variables

#### Observability Stack
- `monitoring/prometheus.yml` - Prometheus scrape configuration
- `monitoring/alert_rules.yml` - Alertmanager rules (high error rate, latency, cache ratio)
- `monitoring/grafana-dashboard.json` - Pre-built Grafana dashboard
- Prometheus metrics exposed at `/metrics/prometheus`
- Metrics: request rate, latency histogram, cache hit ratio, active sessions

#### Notifications Module
- `notifications/__init__.py` - Pluggable notification system
- **EmailBackend**: SMTP and SendGrid support
- **SMSBackend**: Twilio integration with mock fallback
- **WebPushBackend**: Web push notifications (stub)
- **InAppBackend**: In-app notifications stored in memory/DB
- Exponential backoff retry for failed deliveries
- Notification templates for weather alerts, account events

#### CI/CD Pipeline
- `.github/workflows/ci-cd.yml` - GitHub Actions workflow
- Jobs: lint, test, build Docker image, security scan, deploy
- Multi-platform builds (amd64, arm64)
- Conditional deployment to staging/production
- Code coverage upload to Codecov

#### Documentation
- `docs/DEPLOYMENT.md` - Comprehensive deployment guide
- `docs/CDN.md` - Cloudflare and Fastly integration guides
- Edge caching examples with Workers/Compute@Edge
- Cache header configuration

### Changed
- Version bump to 3.0.0
- Updated `config.py` with Phase 3 feature flags
- Enhanced `requirements.txt` with observability dependencies
- Professional UI design comparable to AccuWeather

### Configuration
New environment variables:
- `FEATURE_NOTIFICATIONS` - Enable notifications (default: true)
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` - SMTP settings
- `SENDGRID_API_KEY` - SendGrid API key
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` - Twilio SMS
- `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY` - Web push keys
- `FEATURE_BACKGROUND_JOBS` - Enable job queue (default: true)
- `JOB_QUEUE_BACKEND` - Queue backend (memory/redis/rq/celery)
- `POSTGRES_URL` - PostgreSQL connection URL
- `PROMETHEUS_ENABLED` - Enable Prometheus metrics
- `FEATURE_ANALYTICS`, `FEATURE_REFERRALS`, `FEATURE_SHAREABLE_LINKS` - Growth features
- `FREE_TIER_REQUESTS_PER_DAY`, `PRO_TIER_REQUESTS_PER_DAY` - Access tiers
- `FEATURE_ANIMATIONS`, `REDUCED_MOTION_DEFAULT` - Animation settings

---

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
