# 🚀 Deployment Checklist - IntelliWeather API v3.0.0

Use this checklist to deploy Phase 3 features to production.

---

## Pre-Deployment

### Code Review
- [ ] All Phase 3 files reviewed (`routes/forecast.py`, `modules/weather_insights.py`, `routes/insights.py`)
- [ ] Modified files checked (`app.py`, `config.py`, `routes/geocode.py`)
- [ ] No syntax errors (`get_errors` passed)
- [ ] Import validation passed
- [ ] Route registration verified

### Testing
- [ ] Manual testing of all 13 new endpoints
- [ ] Test nowcast endpoint with valid coordinates
- [ ] Test hourly forecast (24h, 48h, 168h)
- [ ] Test daily forecast (7d, 16d)
- [ ] Test complete forecast package
- [ ] Test all insights endpoints
- [ ] Test autocomplete with partial queries
- [ ] Test popular locations endpoint
- [ ] Test nearby cities endpoint
- [ ] Verify caching works (hit/miss metrics)
- [ ] Test hybrid mode with WeatherAPI fallback
- [ ] Test error handling (invalid coordinates, API failures)

### Documentation
- [ ] PHASE3_README.md reviewed
- [ ] QUICKSTART.md tested
- [ ] CHANGELOG.md updated
- [ ] API documentation accessible at /docs
- [ ] All endpoints documented in OpenAPI spec

---

## Environment Configuration

### Required Environment Variables
```bash
# Core Settings
APP_NAME=IntelliWeather
APP_VERSION=3.0.0
DEBUG=false

# External APIs
WEATHERAPI_KEY=<your_key_here>  # Required for hybrid mode
ENABLE_FALLBACK=true

# Caching
CACHE_TTL_SECONDS=3600
CACHE_MAX_SIZE=1000
GEOCODE_CACHE_TTL_SECONDS=86400

# Rate Limiting
RATE_LIMIT_PER_MIN=60

# Popular Locations (customize)
POPULAR_LOCATIONS=40.7128,-74.0060,New York;51.5074,-0.1278,London;35.6762,139.6503,Tokyo
```

### Optional Configuration
```bash
# Redis (for production caching)
REDIS_URL=redis://localhost:6379/0
SESSION_BACKEND=redis

# PostgreSQL (for production storage)
DB_CONNECTION_STRING=postgresql://user:pass@localhost/intelliweather

# Sentry (error tracking)
SENTRY_DSN=https://your-sentry-dsn

# CORS (adjust for your domain)
CORS_ORIGINS=["https://yourdomain.com"]

# Phase 3 Feature Flags (all enabled by default)
FEATURE_NOWCAST=true
FEATURE_EXTENDED_HOURLY=true
FEATURE_EXTENDED_DAILY=true
FEATURE_HYBRID_FORECAST=true
FEATURE_HEAT_INDEX=true
FEATURE_WIND_CHILL=true
FEATURE_FIRE_RISK=true
FEATURE_UV_EXPOSURE=true
FEATURE_TRAVEL_DISRUPTION=true
FEATURE_COMFORT_INDEX=true
FEATURE_AUTOCOMPLETE=true
FEATURE_NEARBY_CITIES=true
```

---

## Deployment Methods

### Method 1: Docker Compose (Recommended)

#### Checklist:
- [ ] Docker and Docker Compose installed
- [ ] `docker-compose.yml` configured
- [ ] `.env` file created with production values
- [ ] Build image: `docker-compose build`
- [ ] Start services: `docker-compose up -d`
- [ ] Check logs: `docker-compose logs -f app`
- [ ] Verify health: `curl http://localhost:8000/health`
- [ ] Test API: `curl http://localhost:8000/docs`

#### Commands:
```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down

# Restart after changes
docker-compose restart app
```

---

### Method 2: Local Development

#### Checklist:
- [ ] Python 3.8+ installed
- [ ] Virtual environment created
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] `.env` file configured
- [ ] Start server: `python -m uvicorn app:app --host 0.0.0.0 --port 8000`
- [ ] Verify health: `curl http://localhost:8000/health`

#### Commands:
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Start development server
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Or with gunicorn (production)
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

---

### Method 3: Kubernetes

#### Checklist:
- [ ] Kubernetes cluster ready
- [ ] Container image built and pushed
- [ ] ConfigMap created for environment variables
- [ ] Secret created for sensitive values (API keys)
- [ ] Deployment manifest created
- [ ] Service manifest created
- [ ] Ingress configured (optional)
- [ ] Apply manifests: `kubectl apply -f k8s/`
- [ ] Verify pods: `kubectl get pods`
- [ ] Check logs: `kubectl logs -f deployment/intelliweather`

#### Example Deployment:
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: intelliweather
spec:
  replicas: 3
  selector:
    matchLabels:
      app: intelliweather
  template:
    metadata:
      labels:
        app: intelliweather
    spec:
      containers:
      - name: api
        image: intelliweather:3.0.0
        ports:
        - containerPort: 8000
        env:
        - name: APP_VERSION
          value: "3.0.0"
        envFrom:
        - configMapRef:
            name: intelliweather-config
        - secretRef:
            name: intelliweather-secrets
```

---

## Post-Deployment Verification

### Health Checks
```bash
# Basic health
curl http://your-domain.com/health

# Metrics
curl http://your-domain.com/metrics

# API docs
curl http://your-domain.com/docs
```

### Endpoint Testing

#### 1. Nowcast
```bash
curl "http://your-domain.com/api/v3/forecast/nowcast?latitude=40.7128&longitude=-74.0060" | jq .
```
**Expected**: JSON with 15-minute intervals

#### 2. Hourly Forecast
```bash
curl "http://your-domain.com/api/v3/forecast/hourly?latitude=40.7128&longitude=-74.0060&hours=48" | jq .
```
**Expected**: JSON with 48 hourly data points

#### 3. Daily Forecast
```bash
curl "http://your-domain.com/api/v3/forecast/daily?latitude=40.7128&longitude=-74.0060&days=16" | jq .
```
**Expected**: JSON with 16 daily forecasts

#### 4. Weather Insights
```bash
curl "http://your-domain.com/api/v3/insights/current?latitude=40.7128&longitude=-74.0060" | jq .
```
**Expected**: JSON with calculated insights

#### 5. Fire Risk
```bash
curl "http://your-domain.com/api/v3/insights/fire-risk?latitude=34.0522&longitude=-118.2437&days_since_rain=7" | jq .
```
**Expected**: JSON with fire risk score and category

#### 6. Autocomplete
```bash
curl "http://your-domain.com/geocode/autocomplete?q=New%20York" | jq .
```
**Expected**: JSON with location suggestions

---

### Performance Testing

#### Response Times
```bash
# Test nowcast speed
time curl -s "http://your-domain.com/api/v3/forecast/nowcast?latitude=40.7128&longitude=-74.0060" > /dev/null

# Test caching (2nd request should be faster)
time curl -s "http://your-domain.com/api/v3/forecast/nowcast?latitude=40.7128&longitude=-74.0060" > /dev/null
```

**Targets:**
- Nowcast: < 200ms
- Hourly: < 500ms
- Insights: < 100ms
- Autocomplete: < 100ms

#### Cache Hit Ratio
```bash
# Check Prometheus metrics
curl http://your-domain.com/metrics | grep cache_hits_total
curl http://your-domain.com/metrics | grep cache_misses_total
```

**Target**: > 70% hit ratio

---

## Monitoring Setup

### Prometheus Metrics
- [ ] Prometheus scraping configured
- [ ] Metrics endpoint accessible: `/metrics`
- [ ] Custom metrics visible:
  - `api_requests_total`
  - `cache_hits_total`
  - `cache_misses_total`
  - `api_request_duration_seconds`

### Sentry Error Tracking
- [ ] Sentry DSN configured
- [ ] Test error reporting
- [ ] Alerts configured

### Logging
- [ ] Log aggregation configured (if applicable)
- [ ] JSON logging enabled
- [ ] Log levels appropriate for environment

---

## Security Checklist

### API Security
- [ ] Rate limiting enabled
- [ ] CORS configured for production domains
- [ ] HTTPS/TLS enabled (production)
- [ ] API keys hashed (if using API key auth)
- [ ] Session cookies secured (`HTTPONLY`, `SECURE` in production)

### Secret Management
- [ ] No secrets in code
- [ ] Environment variables used for sensitive data
- [ ] `.env` file in `.gitignore`
- [ ] Production secrets in secure vault (AWS Secrets Manager, etc.)

### Network Security
- [ ] Firewall rules configured
- [ ] Only necessary ports exposed
- [ ] DDoS protection enabled (if applicable)

---

## Rollback Plan

### If Issues Occur:

#### Option 1: Feature Flags
```bash
# Disable Phase 3 features via environment
FEATURE_NOWCAST=false
FEATURE_EXTENDED_HOURLY=false
FEATURE_EXTENDED_DAILY=false
# ... etc

# Restart service
docker-compose restart app
```

#### Option 2: Git Rollback
```bash
# Revert to previous version
git revert <commit-hash>
git push origin main

# Redeploy
docker-compose up -d --build
```

#### Option 3: Container Rollback
```bash
# Use previous image
docker pull intelliweather:2.0.0
docker-compose down
# Update docker-compose.yml to use 2.0.0
docker-compose up -d
```

---

## Load Testing (Optional)

### Using Apache Bench
```bash
# Test nowcast endpoint
ab -n 1000 -c 10 "http://your-domain.com/api/v3/forecast/nowcast?latitude=40.7128&longitude=-74.0060"

# Test autocomplete
ab -n 1000 -c 10 "http://your-domain.com/geocode/autocomplete?q=New"
```

### Using Locust
```python
# locustfile.py
from locust import HttpUser, task, between

class WeatherUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def nowcast(self):
        self.client.get("/api/v3/forecast/nowcast?latitude=40.7128&longitude=-74.0060")
    
    @task(2)
    def hourly(self):
        self.client.get("/api/v3/forecast/hourly?latitude=40.7128&longitude=-74.0060&hours=48")
    
    @task(1)
    def insights(self):
        self.client.get("/api/v3/insights/current?latitude=40.7128&longitude=-74.0060")
```

---

## Documentation Deployment

### API Documentation
- [ ] Swagger UI accessible: `/docs`
- [ ] ReDoc accessible: `/redoc`
- [ ] OpenAPI spec downloadable: `/openapi.json`

### User Documentation
- [ ] PHASE3_README.md published
- [ ] QUICKSTART.md accessible
- [ ] CHANGELOG.md updated
- [ ] API examples provided

---

## Communication Plan

### Internal Team
- [ ] Notify developers of new endpoints
- [ ] Share QUICKSTART.md
- [ ] Update internal wiki/docs

### External Users (if applicable)
- [ ] Announce new features
- [ ] Update public API documentation
- [ ] Send migration guide (if needed)
- [ ] Provide example code

---

## Success Criteria

### Functional
- ✅ All 13 new endpoints responding
- ✅ No 500 errors under normal load
- ✅ Caching working correctly
- ✅ Error handling graceful

### Performance
- ✅ Response times within targets
- ✅ Cache hit ratio > 70%
- ✅ No memory leaks
- ✅ CPU usage reasonable

### Business
- ✅ Feature parity with roadmap
- ✅ Documentation complete
- ✅ No breaking changes
- ✅ Ready for user adoption

---

## Final Sign-Off

- [ ] **Development Lead**: Code reviewed and approved
- [ ] **QA Lead**: Testing complete
- [ ] **DevOps Lead**: Deployment successful
- [ ] **Product Owner**: Features validated
- [ ] **Security**: Security review passed

---

## Post-Deployment Tasks

### Week 1
- [ ] Monitor error rates
- [ ] Check performance metrics
- [ ] Review user feedback
- [ ] Fix any critical bugs

### Week 2-4
- [ ] Analyze usage patterns
- [ ] Optimize slow endpoints
- [ ] Plan LEVEL 2 features
- [ ] Write unit tests

### Month 2
- [ ] Performance tuning
- [ ] Documentation improvements
- [ ] Feature enhancements
- [ ] Begin LEVEL 2 implementation

---

**Deployment Date**: _______________  
**Deployed By**: _______________  
**Version**: 3.0.0  
**Status**: ⬜ Planning ⬜ In Progress ⬜ Complete

---

**🎉 Good luck with your deployment!**
