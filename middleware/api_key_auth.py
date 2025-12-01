"""
API Key Authentication Middleware - Complete LEVEL 3 Implementation

Provides API key-based authentication with tiered rate limiting.
"""

import time
from typing import Optional, Dict, Tuple
from collections import defaultdict, deque

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from modules.api_keys import get_api_key_manager
from modules.subscription_tiers import get_tier_limits, SubscriptionTier
from logging_config import get_logger

logger = get_logger(__name__)


class APIKeyRateLimiter:
    """Tiered rate limiter for API keys."""
    
    def __init__(self):
        self.requests: Dict[str, Dict[str, deque]] = defaultdict(
            lambda: {
                "hour": deque(),
                "day": deque(),
                "month": deque()
            }
        )
        
    def _cleanup_old_requests(self, key_id: str, now: float):
        """Remove requests outside the tracking windows."""
        hour_ago = now - 3600
        day_ago = now - 86400
        month_ago = now - 2592000
        
        while self.requests[key_id]["hour"] and self.requests[key_id]["hour"][0] < hour_ago:
            self.requests[key_id]["hour"].popleft()
        
        while self.requests[key_id]["day"] and self.requests[key_id]["day"][0] < day_ago:
            self.requests[key_id]["day"].popleft()
        
        while self.requests[key_id]["month"] and self.requests[key_id]["month"][0] < month_ago:
            self.requests[key_id]["month"].popleft()
    
    def check_and_increment(
        self,
        key_id: str,
        tier: str
    ) -> Tuple[bool, Optional[str], Optional[int]]:
        """Check if request is allowed and increment counter."""
        now = time.time()
        tier_limits = get_tier_limits(tier)
        
        self._cleanup_old_requests(key_id, now)
        
        # Check hourly limit
        hourly_count = len(self.requests[key_id]["hour"])
        if hourly_count >= tier_limits.requests_per_hour:
            oldest = self.requests[key_id]["hour"][0]
            retry_after = int(3600 - (now - oldest))
            return False, "hourly", retry_after
        
        # Check daily limit
        daily_count = len(self.requests[key_id]["day"])
        if daily_count >= tier_limits.requests_per_day:
            oldest = self.requests[key_id]["day"][0]
            retry_after = int(86400 - (now - oldest))
            return False, "daily", retry_after
        
        # Check monthly limit
        monthly_count = len(self.requests[key_id]["month"])
        if monthly_count >= tier_limits.requests_per_month:
            oldest = self.requests[key_id]["month"][0]
            retry_after = int(2592000 - (now - oldest))
            return False, "monthly", retry_after
        
        # All checks passed, record request
        self.requests[key_id]["hour"].append(now)
        self.requests[key_id]["day"].append(now)
        self.requests[key_id]["month"].append(now)
        
        return True, None, None


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Middleware for API key authentication and rate limiting."""
    
    def __init__(self, app):
        super().__init__(app)
        self.rate_limiter = APIKeyRateLimiter()
        self.api_key_manager = get_api_key_manager()
        
        # Paths that don't require API key
        self.excluded_paths = {
            "/", "/docs", "/redoc", "/openapi.json",
            "/auth/", "/metrics", "/health",
            "/static/", "/favicon.ico"
        }
    
    def _is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from API key auth."""
        for excluded in self.excluded_paths:
            if path.startswith(excluded):
                return True
        return False
    
    async def dispatch(self, request: Request, call_next):
        """Process request with API key authentication."""
        path = request.url.path
        
        # Skip excluded paths
        if self._is_excluded_path(path):
            return await call_next(request)
        
        # Extract API key from header
        api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization", "").replace("Bearer ", "")
        
        if not api_key:
            # Allow session-based auth as fallback
            return await call_next(request)
        
        # Validate API key
        start_time = time.time()
        
        try:
            validated_key = self.api_key_manager.validate_key(api_key)
            
            if not validated_key:
                return Response(
                    content='{"detail": "Invalid or expired API key"}',
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    media_type="application/json"
                )
            
            # Check rate limits
            allowed, limit_type, retry_after = self.rate_limiter.check_and_increment(
                validated_key.key_id,
                validated_key.subscription_tier
            )
            
            if not allowed:
                tier_limits = get_tier_limits(validated_key.subscription_tier)
                return Response(
                    content=f'{{"detail": "Rate limit exceeded: {limit_type}", "limit": "{tier_limits.display_name}", "retry_after": {retry_after}}}',
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    media_type="application/json",
                    headers={"Retry-After": str(retry_after)}
                )
            
            # Attach validated key info to request state
            request.state.api_key = validated_key
            request.state.api_authenticated = True
            
            # Process request
            response = await call_next(request)
            
            # Track usage
            latency_ms = (time.time() - start_time) * 1000
            success = 200 <= response.status_code < 400
            
            self.api_key_manager.track_usage(
                key_id=validated_key.key_id,
                user_id=validated_key.user_id,
                endpoint=path,
                method=request.method,
                status_code=response.status_code,
                latency_ms=latency_ms,
                success=success
            )
            
            # Add rate limit headers
            tier_limits = get_tier_limits(validated_key.subscription_tier)
            response.headers["X-RateLimit-Limit"] = str(tier_limits.requests_per_hour)
            response.headers["X-RateLimit-Tier"] = validated_key.subscription_tier
            
            return response
            
        except Exception as e:
            logger.error(f"API key auth error: {e}")
            return Response(
                content='{"detail": "Authentication error"}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                media_type="application/json"
            )


# Global rate limiter instance
_rate_limiter = None


def get_rate_limiter() -> APIKeyRateLimiter:
    """Get global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = APIKeyRateLimiter()
    return _rate_limiter
