# IntelliWeather CDN Integration Guide

This guide covers integrating IntelliWeather with Content Delivery Networks (CDNs) for improved performance and global distribution.

## Table of Contents

- [Overview](#overview)
- [Cloudflare Setup](#cloudflare-setup)
- [Fastly Setup](#fastly-setup)
- [Cache Headers](#cache-headers)
- [Edge Computing](#edge-computing)
- [Best Practices](#best-practices)

---

## Overview

CDN integration provides:

- **Reduced latency** - Serve content from edge locations closer to users
- **Improved availability** - Multiple origin servers and failover
- **DDoS protection** - Built-in protection at the edge
- **SSL/TLS termination** - Handle HTTPS at the edge
- **Caching** - Reduce load on origin servers

### What to Cache

| Content Type | Cache Duration | Notes |
|-------------|----------------|-------|
| Static assets (CSS, JS, images) | 1 year | Versioned filenames recommended |
| Weather data (current) | 5-15 minutes | Short TTL for freshness |
| Weather data (forecast) | 30-60 minutes | Longer TTL acceptable |
| Geocoding results | 24 hours | Rarely changes |
| API documentation | 1 hour | Semi-static |
| Authentication endpoints | No cache | Always bypass |

---

## Cloudflare Setup

### DNS Configuration

```
# Point your domain to Cloudflare
weather.example.com    A    <cloudflare-ip>
weather.example.com    AAAA <cloudflare-ipv6>
```

### Page Rules

```
# Cache static assets
URL: weather.example.com/static/*
Settings:
  - Cache Level: Cache Everything
  - Edge Cache TTL: 1 month
  - Browser Cache TTL: 1 year

# Cache weather API with short TTL
URL: weather.example.com/weather*
Settings:
  - Cache Level: Cache Everything
  - Edge Cache TTL: 5 minutes
  - Origin Cache Control: On

# Bypass cache for auth
URL: weather.example.com/auth/*
Settings:
  - Cache Level: Bypass
  - Security Level: High
```

### Cache Rules (Modern)

```json
// Cloudflare Dashboard > Rules > Cache Rules

// Rule 1: Static Assets
{
  "expression": "(http.request.uri.path starts_with \"/static\")",
  "action": "cache",
  "cache_ttl": {
    "default": 2592000
  }
}

// Rule 2: Weather API
{
  "expression": "(http.request.uri.path starts_with \"/weather\")",
  "action": "cache",
  "cache_ttl": {
    "default": 300
  },
  "cache_key": {
    "query_string": {
      "include": ["lat", "lon", "units"]
    }
  }
}

// Rule 3: Bypass Auth
{
  "expression": "(http.request.uri.path starts_with \"/auth\")",
  "action": "bypass"
}
```

### Cloudflare Worker (Edge Caching)

```javascript
// workers/weather-cache.js
// Intelligent edge caching for weather data

const CACHE_CONFIG = {
  '/weather': { ttl: 300, vary: ['lat', 'lon'] },
  '/forecast': { ttl: 1800, vary: ['lat', 'lon', 'days'] },
  '/geocode': { ttl: 86400, vary: ['q'] },
  '/hourly': { ttl: 900, vary: ['lat', 'lon'] },
};

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  const url = new URL(request.url);
  const path = url.pathname;
  
  // Find matching cache config
  const config = Object.entries(CACHE_CONFIG).find(([p]) => path.startsWith(p));
  
  if (!config) {
    // No caching - pass through
    return fetch(request);
  }
  
  const [, { ttl, vary }] = config;
  
  // Build cache key from path and vary parameters
  const cacheKey = buildCacheKey(url, vary);
  const cache = caches.default;
  
  // Check cache
  let response = await cache.match(cacheKey);
  
  if (response) {
    // Cache hit - add header for debugging
    response = new Response(response.body, response);
    response.headers.set('X-Cache', 'HIT');
    response.headers.set('X-Cache-Key', cacheKey);
    return response;
  }
  
  // Cache miss - fetch from origin
  response = await fetch(request);
  
  if (response.ok) {
    // Clone response for caching
    const responseToCache = new Response(response.body, response);
    responseToCache.headers.set('Cache-Control', `public, max-age=${ttl}`);
    responseToCache.headers.set('X-Cache', 'MISS');
    
    // Store in cache
    event.waitUntil(cache.put(cacheKey, responseToCache.clone()));
    
    return responseToCache;
  }
  
  return response;
}

function buildCacheKey(url, varyParams) {
  const params = new URLSearchParams();
  
  for (const param of varyParams) {
    const value = url.searchParams.get(param);
    if (value) {
      // Round coordinates for better cache hit ratio
      if (param === 'lat' || param === 'lon') {
        params.set(param, parseFloat(value).toFixed(2));
      } else {
        params.set(param, value);
      }
    }
  }
  
  return `${url.origin}${url.pathname}?${params.toString()}`;
}
```

### Deploying the Worker

```bash
# Install Wrangler CLI
npm install -g wrangler

# Login to Cloudflare
wrangler login

# Create wrangler.toml
cat > wrangler.toml << EOF
name = "weather-cache"
main = "workers/weather-cache.js"
compatibility_date = "2024-01-01"

[env.production]
route = "weather.example.com/*"
EOF

# Deploy
wrangler deploy --env production
```

---

## Fastly Setup

### VCL Configuration

```vcl
// Fastly VCL for IntelliWeather

sub vcl_recv {
  // Normalize query parameters for better cache hit ratio
  if (req.url ~ "^/weather" || req.url ~ "^/forecast") {
    // Round coordinates to 2 decimal places
    set req.url = querystring.filter_except(req.url, "lat" "lon" "units" "format");
  }
  
  // Bypass cache for auth endpoints
  if (req.url ~ "^/auth") {
    return(pass);
  }
  
  // Bypass cache for POST/PUT/DELETE
  if (req.method != "GET" && req.method != "HEAD") {
    return(pass);
  }
}

sub vcl_backend_response {
  // Set cache TTL based on path
  if (req.url ~ "^/static") {
    set beresp.ttl = 30d;
    set beresp.http.Cache-Control = "public, max-age=2592000";
  } else if (req.url ~ "^/weather") {
    set beresp.ttl = 5m;
    set beresp.http.Surrogate-Control = "max-age=300";
  } else if (req.url ~ "^/forecast") {
    set beresp.ttl = 30m;
    set beresp.http.Surrogate-Control = "max-age=1800";
  } else if (req.url ~ "^/geocode") {
    set beresp.ttl = 24h;
    set beresp.http.Surrogate-Control = "max-age=86400";
  }
  
  // Add debug headers
  set beresp.http.X-Cache-TTL = beresp.ttl;
}

sub vcl_deliver {
  // Add cache status header
  if (obj.hits > 0) {
    set resp.http.X-Cache = "HIT";
    set resp.http.X-Cache-Hits = obj.hits;
  } else {
    set resp.http.X-Cache = "MISS";
  }
}
```

### Fastly Compute@Edge (Rust)

```rust
// src/main.rs
use fastly::http::{header, Method, StatusCode};
use fastly::{mime, Error, Request, Response};
use std::collections::HashMap;

const BACKEND_NAME: &str = "origin";

#[fastly::main]
fn main(req: Request) -> Result<Response, Error> {
    let path = req.get_path();
    
    // Route based on path
    match path {
        p if p.starts_with("/static") => handle_static(req),
        p if p.starts_with("/weather") => handle_weather(req, 300),
        p if p.starts_with("/forecast") => handle_weather(req, 1800),
        p if p.starts_with("/geocode") => handle_weather(req, 86400),
        p if p.starts_with("/auth") => handle_passthrough(req),
        _ => handle_passthrough(req),
    }
}

fn handle_static(req: Request) -> Result<Response, Error> {
    let mut resp = req.send(BACKEND_NAME)?;
    resp.set_header(header::CACHE_CONTROL, "public, max-age=2592000");
    Ok(resp)
}

fn handle_weather(mut req: Request, ttl: u64) -> Result<Response, Error> {
    // Normalize coordinates
    let url = req.get_url_mut();
    if let Some(lat) = url.query_pairs().find(|(k, _)| k == "lat") {
        let rounded = (lat.1.parse::<f64>().unwrap_or(0.0) * 100.0).round() / 100.0;
        // Update query parameter
    }
    
    let mut resp = req.send(BACKEND_NAME)?;
    resp.set_header(
        header::CACHE_CONTROL, 
        &format!("public, max-age={}", ttl)
    );
    Ok(resp)
}

fn handle_passthrough(req: Request) -> Result<Response, Error> {
    let mut resp = req.send(BACKEND_NAME)?;
    resp.set_header(header::CACHE_CONTROL, "no-store");
    Ok(resp)
}
```

---

## Cache Headers

### Origin Server Configuration

Update `app.py` to include proper cache headers:

```python
from fastapi import Response
from datetime import timedelta

# Middleware to add cache headers
@app.middleware("http")
async def add_cache_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path
    
    # Static assets
    if path.startswith("/static"):
        response.headers["Cache-Control"] = "public, max-age=2592000"
        response.headers["Surrogate-Control"] = "max-age=2592000"
    
    # Weather endpoints
    elif path.startswith("/weather"):
        response.headers["Cache-Control"] = "public, max-age=300"
        response.headers["Surrogate-Control"] = "max-age=300"
        response.headers["Vary"] = "Accept-Encoding"
    
    # Forecast endpoints
    elif path.startswith("/forecast"):
        response.headers["Cache-Control"] = "public, max-age=1800"
        response.headers["Surrogate-Control"] = "max-age=1800"
    
    # Geocoding
    elif path.startswith("/geocode"):
        response.headers["Cache-Control"] = "public, max-age=86400"
        response.headers["Surrogate-Control"] = "max-age=86400"
    
    # Auth - no cache
    elif path.startswith("/auth"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    
    return response
```

### Cache-Control Headers

| Header | Description |
|--------|-------------|
| `Cache-Control: public, max-age=300` | Cache for 5 minutes |
| `Surrogate-Control: max-age=300` | CDN-specific TTL |
| `Vary: Accept-Encoding` | Cache separately for gzip/brotli |
| `ETag: "abc123"` | Content-based validation |
| `Last-Modified: <date>` | Time-based validation |

---

## Best Practices

### 1. Normalize Cache Keys

```javascript
// Round coordinates to reduce cache variants
const lat = Math.round(lat * 100) / 100;  // 40.7128 -> 40.71
const lon = Math.round(lon * 100) / 100;
```

### 2. Cache Warming

```bash
# Pre-warm cache for popular locations
LOCATIONS=(
  "40.71,-74.01"    # New York
  "51.51,-0.13"     # London
  "35.68,139.65"    # Tokyo
)

for loc in "${LOCATIONS[@]}"; do
  IFS=',' read -r lat lon <<< "$loc"
  curl -s "https://weather.example.com/weather?lat=$lat&lon=$lon" > /dev/null
  curl -s "https://weather.example.com/forecast?lat=$lat&lon=$lon" > /dev/null
done
```

### 3. Cache Purging

```bash
# Cloudflare - purge specific URLs
curl -X POST "https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache" \
  -H "Authorization: Bearer {api_token}" \
  -H "Content-Type: application/json" \
  --data '{"files":["https://weather.example.com/weather?lat=40.71&lon=-74.01"]}'

# Cloudflare - purge everything
curl -X POST "https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache" \
  -H "Authorization: Bearer {api_token}" \
  -H "Content-Type: application/json" \
  --data '{"purge_everything":true}'

# Fastly
curl -X POST "https://api.fastly.com/service/{service_id}/purge_all" \
  -H "Fastly-Key: {api_key}"
```

### 4. Monitor Cache Performance

```bash
# Check cache hit ratio (Cloudflare)
curl -s "https://api.cloudflare.com/client/v4/zones/{zone_id}/analytics/dashboard" \
  -H "Authorization: Bearer {api_token}" | jq '.result.totals.requests.cached'

# Check headers
curl -I "https://weather.example.com/weather?lat=40.71&lon=-74.01"
# Look for: X-Cache: HIT, CF-Cache-Status: HIT
```

---

## Summary

1. **Use CDN for all traffic** - Better performance and security
2. **Set appropriate TTLs** - Balance freshness vs. efficiency
3. **Normalize cache keys** - Reduce variants for better hit ratio
4. **Bypass cache for auth** - Never cache authenticated requests
5. **Monitor cache performance** - Track hit ratios and optimize
