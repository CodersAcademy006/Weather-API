# 🧪 QA Checklist - IntelliWeather API

This document provides a comprehensive QA checklist for testing all features of the IntelliWeather API.

---

## 1. User Authentication

### 1.1 Signup
- [ ] **Valid signup**: Create account with valid email, username, and strong password
- [ ] **Duplicate email**: Attempt signup with existing email → should fail
- [ ] **Duplicate username**: Attempt signup with existing username → should fail
- [ ] **Weak password**: Attempt signup with password < 8 chars → should fail
- [ ] **Invalid email**: Attempt signup with invalid email format → should fail
- [ ] **Session created**: After signup, session cookie should be set

```bash
# Test signup
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"TestPass123"}' \
  -c cookies.txt -v
```

### 1.2 Login
- [ ] **Valid login**: Login with correct credentials
- [ ] **Invalid email**: Login with non-existent email → should fail
- [ ] **Invalid password**: Login with wrong password → should fail
- [ ] **Session created**: After login, session cookie should be set

```bash
# Test login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass123"}' \
  -c cookies.txt -v
```

### 1.3 Logout
- [ ] **Valid logout**: Logout invalidates session
- [ ] **Cookie cleared**: Session cookie should be removed

```bash
# Test logout
curl -X POST http://localhost:8000/auth/logout \
  -b cookies.txt -v
```

### 1.4 Session Management
- [ ] **Session persists**: Authenticated requests work with session cookie
- [ ] **Session timeout**: Session expires after configured timeout
- [ ] **Protected endpoints**: `/auth/me` requires authentication

```bash
# Test protected endpoint
curl http://localhost:8000/auth/me \
  -b cookies.txt
```

---

## 2. Weather API Endpoints

### 2.1 Current Weather (`/weather`)
- [ ] **Valid request**: Get weather for valid coordinates
- [ ] **Cache miss**: First request fetches from API (check logs)
- [ ] **Cache hit**: Second request uses cache (check logs)
- [ ] **Invalid coordinates**: Handle edge cases (extreme lat/lon)

```bash
# Test weather endpoint
curl "http://localhost:8000/weather?lat=40.71&lon=-74.01"

# Check for cache behavior
curl "http://localhost:8000/weather?lat=40.71&lon=-74.01"  # Should be cache hit
```

### 2.2 Hourly Forecast (`/hourly`)
- [ ] **Returns 24 hours**: Response contains 24 hourly entries
- [ ] **Cache behavior**: Check cache hit/miss in logs

```bash
curl "http://localhost:8000/hourly?lat=40.71&lon=-74.01"
```

### 2.3 Daily Forecast (`/forecast`)
- [ ] **Returns 7 days**: Response contains 7 daily entries
- [ ] **Contains all fields**: max_temp, min_temp, sunrise, sunset, etc.

```bash
curl "http://localhost:8000/forecast?lat=40.71&lon=-74.01"
```

### 2.4 AQI & Alerts (`/aqi-alerts`)
- [ ] **Returns AQI data**: Response contains US AQI values
- [ ] **Shorter cache TTL**: AQI cached for 30 minutes (not 1 hour)

```bash
curl "http://localhost:8000/aqi-alerts?lat=40.71&lon=-74.01"
```

---

## 3. Caching System

### 3.1 In-Memory Cache
- [ ] **Cache set/get**: Values stored and retrieved correctly
- [ ] **TTL expiration**: Cached items expire after TTL
- [ ] **Cache stats**: `/metrics` shows hit/miss counts

```bash
# Check cache stats
curl http://localhost:8000/metrics | jq '.cache'
```

### 3.2 Cache Hit/Miss Demonstration
1. Clear the cache (restart the server)
2. Make first request → logs show "CACHE MISS"
3. Make same request → logs show "CACHE HIT"
4. Wait for TTL to expire
5. Make same request → logs show "CACHE MISS" again

---

## 4. Rate Limiting

### 4.1 Within Limits
- [ ] **Requests allowed**: First 60 requests succeed
- [ ] **Headers present**: `X-RateLimit-Limit` and `X-RateLimit-Remaining` in response

```bash
# Check rate limit headers
curl -v "http://localhost:8000/weather?lat=40.71&lon=-74.01" 2>&1 | grep -i ratelimit
```

### 4.2 Exceeding Limits
- [ ] **429 response**: Returns "Too Many Requests" after limit
- [ ] **Retry-After header**: Response includes when to retry

```bash
# Rapid requests to trigger rate limit
for i in {1..70}; do
  curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:8000/weather?lat=40.71&lon=-74.01"
done
```

---

## 5. Health & Metrics

### 5.1 Health Check (`/healthz`)
- [ ] **Returns healthy**: All components pass checks
- [ ] **Storage check**: Storage is writable
- [ ] **Cache check**: Cache is operational
- [ ] **Session middleware**: Middleware is loaded

```bash
curl http://localhost:8000/healthz | jq
```

### 5.2 Metrics (`/metrics`)
- [ ] **Counters present**: total_requests, cache_hits, cache_misses
- [ ] **Active sessions**: Shows count of active sessions
- [ ] **Uptime**: Shows application uptime

```bash
curl http://localhost:8000/metrics | jq
```

### 5.3 Prometheus Format (`/metrics/prometheus`)
- [ ] **Valid format**: Output matches Prometheus text format

```bash
curl http://localhost:8000/metrics/prometheus
```

---

## 6. Docker & Load Balancing

### 6.1 Docker Build
- [ ] **Build succeeds**: `docker build -t intelliweather .`
- [ ] **Image runs**: `docker run -p 8000:8000 intelliweather`

### 6.2 Docker Compose
- [ ] **All services start**: `docker-compose up -d`
- [ ] **Multiple replicas**: `docker-compose up -d --scale app=3`
- [ ] **Health checks pass**: All containers healthy

```bash
docker-compose up -d --scale app=3
docker-compose ps
```

### 6.3 Load Balancing
- [ ] **Requests distributed**: Check NGINX logs for distribution
- [ ] **Failover works**: Stop one replica, requests continue

```bash
# Test load balancing
for i in {1..10}; do
  curl -s http://localhost/weather?lat=40.71&lon=-74.01 > /dev/null
done

# Check NGINX logs
docker-compose logs nginx | tail -20
```

---

## 7. Security

### 7.1 Authentication
- [ ] **Passwords hashed**: Passwords stored with bcrypt
- [ ] **Session cookies secure**: httpOnly, SameSite flags set

### 7.2 Input Validation
- [ ] **Email validation**: Invalid emails rejected
- [ ] **Password requirements**: Weak passwords rejected
- [ ] **SQL injection**: Special characters handled safely

### 7.3 CORS
- [ ] **Headers present**: CORS headers in responses

---

## 8. Error Handling

### 8.1 API Errors
- [ ] **Invalid parameters**: Returns 422 with details
- [ ] **External API failure**: Returns 500 with message
- [ ] **Not found**: Returns 404 for invalid routes

```bash
# Test invalid parameters
curl "http://localhost:8000/weather?lat=invalid&lon=-74.01"

# Test non-existent endpoint
curl http://localhost:8000/nonexistent
```

---

## 9. Performance

### 9.1 Response Times
- [ ] **Cache hit < 50ms**: Cached responses are fast
- [ ] **API call < 2s**: External API calls complete quickly

```bash
# Measure response time
time curl "http://localhost:8000/weather?lat=40.71&lon=-74.01"
```

### 9.2 Concurrent Requests
- [ ] **Handles 100 concurrent**: No crashes or errors

```bash
# Using Apache Bench (if available)
ab -n 100 -c 10 "http://localhost:8000/weather?lat=40.71&lon=-74.01"
```

---

## Checklist Summary

| Category | Tests | Status |
|----------|-------|--------|
| Authentication | 10 | ⬜ |
| Weather API | 8 | ⬜ |
| Caching | 4 | ⬜ |
| Rate Limiting | 4 | ⬜ |
| Health & Metrics | 6 | ⬜ |
| Docker | 6 | ⬜ |
| Security | 5 | ⬜ |
| Error Handling | 3 | ⬜ |
| Performance | 3 | ⬜ |
| **Total** | **49** | ⬜ |

---

## Test Execution

```bash
# Run all unit tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test file
pytest tests/test_modules.py -v
```
