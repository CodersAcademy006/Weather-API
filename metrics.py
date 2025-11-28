"""
Metrics and Health Check Module

This module provides:
- /healthz endpoint for health checks
- /metrics endpoint for observability
- In-memory counters for request tracking
"""

import threading
from typing import Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status
from storage import get_storage
from cache import get_cache
from session_middleware import get_session_middleware
from middleware.rate_limiter import get_rate_limiter
from config import settings
from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Health & Metrics"])


class Metrics:
    """
    Thread-safe metrics collector.
    
    Tracks various application metrics including request counts,
    cache performance, and error rates.
    """
    
    def __init__(self):
        self._lock = threading.RLock()
        self._counters: Dict[str, int] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "weather_requests": 0,
            "hourly_requests": 0,
            "forecast_requests": 0,
            "aqi_requests": 0,
            "auth_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "rate_limit_exceeded": 0,
        }
        self._start_time = datetime.now(timezone.utc)
    
    def increment(self, counter: str, value: int = 1) -> None:
        """Increment a counter."""
        with self._lock:
            if counter in self._counters:
                self._counters[counter] += value
            else:
                self._counters[counter] = value
    
    def get(self, counter: str) -> int:
        """Get a counter value."""
        with self._lock:
            return self._counters.get(counter, 0)
    
    def get_all(self) -> Dict[str, int]:
        """Get all counters."""
        with self._lock:
            return self._counters.copy()
    
    def reset(self) -> None:
        """Reset all counters."""
        with self._lock:
            for key in self._counters:
                self._counters[key] = 0
    
    def uptime_seconds(self) -> float:
        """Get application uptime in seconds."""
        return (datetime.now(timezone.utc) - self._start_time).total_seconds()


# Global metrics instance
_metrics: Metrics = None


def get_metrics() -> Metrics:
    """Get the global metrics instance."""
    global _metrics
    if _metrics is None:
        _metrics = Metrics()
    return _metrics


def init_metrics() -> Metrics:
    """Initialize the global metrics instance."""
    global _metrics
    _metrics = Metrics()
    return _metrics


# ==================== HEALTH CHECK ====================

@router.get("/healthz")
async def health_check():
    """
    Health check endpoint.
    
    Checks:
    - Storage is writable
    - Cache is working
    - Session middleware is loaded
    
    Returns:
        Health status with component checks
    """
    checks = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {}
    }
    
    all_healthy = True
    
    # Check storage
    try:
        storage = get_storage()
        storage_healthy = storage.is_writable()
        checks["checks"]["storage"] = {
            "status": "healthy" if storage_healthy else "unhealthy",
            "writable": storage_healthy
        }
        if not storage_healthy:
            all_healthy = False
    except Exception as e:
        checks["checks"]["storage"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        all_healthy = False
    
    # Check cache
    try:
        cache = get_cache()
        # Test cache operations
        test_key = "__health_check__"
        cache.set(test_key, "test", ttl=10)
        cache_value = cache.get(test_key)
        cache.delete(test_key)
        cache_healthy = cache_value == "test"
        
        checks["checks"]["cache"] = {
            "status": "healthy" if cache_healthy else "unhealthy",
            "size": cache.size(),
            "stats": cache.stats()
        }
        if not cache_healthy:
            all_healthy = False
    except Exception as e:
        checks["checks"]["cache"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        all_healthy = False
    
    # Check session middleware
    try:
        session_middleware = get_session_middleware()
        session_loaded = session_middleware is not None
        
        checks["checks"]["session_middleware"] = {
            "status": "healthy" if session_loaded else "not_loaded",
            "loaded": session_loaded
        }
    except Exception as e:
        checks["checks"]["session_middleware"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Overall status
    if not all_healthy:
        checks["status"] = "unhealthy"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=checks
        )
    
    return checks


# ==================== METRICS ====================

@router.get("/metrics")
async def get_metrics_endpoint():
    """
    Metrics endpoint.
    
    Exposes counters for:
    - Total requests
    - Cache hits/misses
    - Active sessions
    - Rate limit events
    - Uptime
    
    Returns:
        Application metrics
    """
    metrics = get_metrics()
    
    # Get cache stats
    try:
        cache = get_cache()
        cache_stats = cache.stats()
    except Exception:
        cache_stats = {}
    
    # Get storage stats
    try:
        storage = get_storage()
        storage_stats = storage.get_stats()
        active_sessions = storage_stats.get("sessions_count", 0)
    except Exception:
        storage_stats = {}
        active_sessions = 0
    
    # Get rate limiter stats
    try:
        rate_limiter = get_rate_limiter()
        rate_limiter_stats = rate_limiter.stats() if rate_limiter else {}
    except Exception:
        rate_limiter_stats = {}
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": round(metrics.uptime_seconds(), 2),
        "counters": metrics.get_all(),
        "cache": cache_stats,
        "storage": storage_stats,
        "rate_limiter": rate_limiter_stats,
        "active_sessions": active_sessions,
        "app_info": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": "development" if settings.DEBUG else "production"
        }
    }


# ==================== PROMETHEUS FORMAT (Optional) ====================

@router.get("/metrics/prometheus")
async def get_prometheus_metrics():
    """
    Metrics in Prometheus format.
    
    Returns metrics in Prometheus text exposition format.
    """
    metrics = get_metrics()
    counters = metrics.get_all()
    
    lines = [
        "# HELP intelliweather_requests_total Total number of requests",
        "# TYPE intelliweather_requests_total counter",
        f"intelliweather_requests_total {counters.get('total_requests', 0)}",
        "",
        "# HELP intelliweather_cache_hits_total Total cache hits",
        "# TYPE intelliweather_cache_hits_total counter",
        f"intelliweather_cache_hits_total {counters.get('cache_hits', 0)}",
        "",
        "# HELP intelliweather_cache_misses_total Total cache misses",
        "# TYPE intelliweather_cache_misses_total counter",
        f"intelliweather_cache_misses_total {counters.get('cache_misses', 0)}",
        "",
        "# HELP intelliweather_uptime_seconds Application uptime in seconds",
        "# TYPE intelliweather_uptime_seconds gauge",
        f"intelliweather_uptime_seconds {round(metrics.uptime_seconds(), 2)}",
    ]
    
    # Get active sessions
    try:
        storage = get_storage()
        active_sessions = storage.count_active_sessions()
        lines.extend([
            "",
            "# HELP intelliweather_active_sessions Number of active sessions",
            "# TYPE intelliweather_active_sessions gauge",
            f"intelliweather_active_sessions {active_sessions}",
        ])
    except Exception:
        pass
    
    return "\n".join(lines) + "\n"
