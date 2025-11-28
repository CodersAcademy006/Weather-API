# 🎓 Demo Script - IntelliWeather API

## Final Year Project Presentation Guide

This guide provides step-by-step instructions for demonstrating the IntelliWeather API to judges and examiners.

---

## 📋 Pre-Demo Setup (10 minutes before)

### 1. Start the Services

```bash
# Navigate to project directory
cd Weather-API

# Option A: Local development
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Option B: Docker (recommended for demo)
docker-compose up -d --scale app=2
```

### 2. Verify Services Running

```bash
# Check health
curl http://localhost:8000/healthz

# Expected output:
# {"status":"healthy","timestamp":"...","checks":{...}}
```

### 3. Open Browser Tabs
- Tab 1: http://localhost:8000 (Dashboard)
- Tab 2: http://localhost:8000/docs (API Documentation)
- Tab 3: Terminal for curl commands

---

## 🎬 Demo Presentation (15-20 minutes)

### Part 1: UI Dashboard (3 minutes)

**Show the modern weather dashboard:**

1. Open http://localhost:8000 in browser
2. Point out key features:
   - Glassmorphism design with backdrop blur
   - Dynamic gradient background
   - Connection status indicator (top right)
   - Responsive layout

3. Search for a city:
   - Type "London" in search box
   - Show autocomplete suggestions
   - Select a city to load weather

4. Navigate tabs:
   - **Now**: Current weather with details
   - **Hourly**: 24-hour forecast with scroll
   - **7-Day**: Weekly forecast

**Talking Points:**
> "This is our production-ready weather dashboard. Notice the modern glassmorphism design that changes based on weather conditions. The connection indicator shows real-time backend connectivity."

---

### Part 2: API Endpoints (4 minutes)

**Open the Swagger docs:**

1. Navigate to http://localhost:8000/docs
2. Show the available endpoints:
   - `/weather` - Current conditions
   - `/hourly` - Hourly forecast
   - `/forecast` - 7-day forecast
   - `/aqi-alerts` - Air quality

3. **Live API Call Demo:**

```bash
# In terminal, show a weather request
curl "http://localhost:8000/weather?lat=40.71&lon=-74.01" | jq

# Expected output:
# {
#   "source": "live",  # or "cache"
#   "temperature_c": 22.5,
#   "humidity_pct": 65,
#   ...
# }
```

**Talking Points:**
> "Our API follows REST principles with standardized JSON responses. We use Open-Meteo as our weather data provider, which gives us global coverage without API key requirements."

---

### Part 3: Caching System (4 minutes)

**Demonstrate cache behavior:**

1. **First request (cache miss):**
```bash
# Clear any existing cache by restarting, then:
curl "http://localhost:8000/weather?lat=51.51&lon=-0.13"
# Check logs: "CACHE MISS for current weather"
```

2. **Second request (cache hit):**
```bash
curl "http://localhost:8000/weather?lat=51.51&lon=-0.13"
# Check logs: "CACHE HIT for current weather"
```

3. **Show cache statistics:**
```bash
curl http://localhost:8000/metrics | jq '.cache'
# Shows: hits, misses, hit_rate_percent
```

**Talking Points:**
> "We implemented a multi-tier caching strategy. First, we check our in-memory cache with configurable TTL. This dramatically reduces API calls and improves response times from ~500ms to under 10ms."

---

### Part 4: User Authentication (3 minutes)

**Demonstrate signup/login flow:**

1. **Create account:**
```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"username":"demo_user","email":"demo@test.com","password":"DemoPass123"}' \
  -c cookies.txt
```

2. **Check session:**
```bash
curl http://localhost:8000/auth/session -b cookies.txt
# Shows authenticated: true
```

3. **Access protected endpoint:**
```bash
curl http://localhost:8000/auth/me -b cookies.txt
# Returns user info
```

4. **Logout:**
```bash
curl -X POST http://localhost:8000/auth/logout -b cookies.txt
```

**Talking Points:**
> "Our authentication uses secure server-side sessions with bcrypt password hashing. Sessions are stored in CSV files for simplicity, but we've designed it to easily swap to Redis for production scale."

---

### Part 5: Rate Limiting (2 minutes)

**Demonstrate rate limiting:**

```bash
# Rapid requests
for i in {1..70}; do
  echo -n "Request $i: "
  curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/weather?lat=40.71&lon=-74.01"
  echo
done

# After ~60 requests, you'll see 429 (Too Many Requests)
```

**Talking Points:**
> "Rate limiting protects our service from abuse. We use a sliding window algorithm that allows 60 requests per minute per IP address. Clients receive helpful headers showing remaining quota."

---

### Part 6: Health & Metrics (2 minutes)

**Show observability endpoints:**

1. **Health check:**
```bash
curl http://localhost:8000/healthz | jq
```

2. **Metrics:**
```bash
curl http://localhost:8000/metrics | jq
```

**Talking Points:**
> "For production monitoring, we expose health checks for load balancers and detailed metrics including request counts, cache performance, and active sessions. This integrates with Prometheus and Grafana for dashboards."

---

### Part 7: Docker & Scaling (3 minutes)

**Show containerized deployment:**

```bash
# Show running containers
docker-compose ps

# Scale up
docker-compose up -d --scale app=3

# Verify 3 replicas
docker-compose ps

# Show load balancing
for i in {1..6}; do
  curl -s http://localhost/healthz > /dev/null
done
docker-compose logs nginx | tail -10
```

**Talking Points:**
> "Our application is fully containerized with Docker. The docker-compose setup includes NGINX as a load balancer distributing traffic across multiple app replicas. This allows horizontal scaling to handle increased traffic."

---

## 🏆 Key Points to Emphasize

### Technical Achievements
1. **Modern Stack**: FastAPI + Python 3.11
2. **Production Patterns**: Caching, rate limiting, health checks
3. **Clean Architecture**: Modular design with separation of concerns
4. **Type Safety**: Full type hints throughout
5. **Testing**: Comprehensive unit tests

### Competitive Advantages vs AccuWeather
1. **Free & Open**: No API key required (Open-Meteo)
2. **Self-Hosted**: Full control over data
3. **Modern UI**: Glassmorphism design
4. **Lightweight**: Minimal dependencies
5. **Scalable**: Docker-ready

### Production Readiness
1. ✅ In-memory caching with TTL
2. ✅ CSV-based persistence (upgradeable to PostgreSQL)
3. ✅ Session management
4. ✅ Rate limiting
5. ✅ Health checks
6. ✅ Metrics/observability
7. ✅ Docker containerization
8. ✅ NGINX load balancing

---

## 🎯 Answers to Common Questions

**Q: Why CSV storage instead of a database?**
> "CSV storage provides simplicity for demonstration and development. The storage layer is abstracted, making it easy to swap in PostgreSQL or any other database without changing application code."

**Q: How does the caching work?**
> "We use a multi-tier approach: in-memory cache checked first (fastest), then database cache, then external API. The in-memory cache uses LRU eviction with configurable TTL."

**Q: Can this scale to handle more users?**
> "Yes! The Docker setup supports horizontal scaling. Add more replicas with `--scale app=N`. For persistent sessions across replicas, we'd switch to Redis (already scaffolded in the code)."

**Q: How secure is the authentication?**
> "Passwords are hashed with bcrypt (work factor 12). Sessions use secure, httpOnly cookies. The rate limiter prevents brute force attacks."

**Q: What would you improve for production?**
> "Redis for sessions, PostgreSQL for persistence, Sentry for error tracking (already integrated), and Kubernetes for orchestration."

---

## 📸 Screenshot Opportunities

1. Dashboard with weather data loaded
2. Swagger API documentation page
3. Terminal showing cache hit/miss logs
4. Metrics endpoint output
5. Docker containers running
6. Rate limit 429 response

---

## ⏱️ Timing Summary

| Section | Duration |
|---------|----------|
| UI Dashboard | 3 min |
| API Endpoints | 4 min |
| Caching System | 4 min |
| Authentication | 3 min |
| Rate Limiting | 2 min |
| Health & Metrics | 2 min |
| Docker & Scaling | 3 min |
| **Total** | **~20 min** |

---

Good luck with your presentation! 🎉
