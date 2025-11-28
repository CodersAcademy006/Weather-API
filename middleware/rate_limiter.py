"""
Per-IP Rate Limiter Middleware

This module provides rate limiting functionality with:
- Configurable requests per minute per IP
- Sliding window algorithm
- In-memory storage
- Thread-safe operations
"""

import threading
import time
from typing import Dict, List, Callable, Tuple
from collections import defaultdict
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from config import settings
from logging_config import get_logger

logger = get_logger(__name__)


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)}
        )


class SlidingWindowRateLimiter:
    """
    Thread-safe sliding window rate limiter.
    
    Uses a sliding window algorithm to track requests per IP.
    """
    
    def __init__(
        self,
        requests_per_window: int = None,
        window_seconds: int = None
    ):
        """
        Initialize the rate limiter.
        
        Args:
            requests_per_window: Maximum requests allowed per window
            window_seconds: Window size in seconds
        """
        self.requests_per_window = requests_per_window or settings.RATE_LIMIT_PER_MIN
        self.window_seconds = window_seconds or settings.RATE_LIMIT_WINDOW_SECONDS
        
        # Store timestamps of requests per IP
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.RLock()
        
        # Statistics
        self._total_requests = 0
        self._blocked_requests = 0
        
        logger.info(
            f"Rate limiter initialized: {self.requests_per_window} requests "
            f"per {self.window_seconds} seconds"
        )
    
    def is_allowed(self, identifier: str) -> Tuple[bool, int]:
        """
        Check if a request is allowed for the given identifier.
        
        Args:
            identifier: Unique identifier (usually IP address)
            
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        now = time.time()
        window_start = now - self.window_seconds
        
        with self._lock:
            self._total_requests += 1
            
            # Clean up old timestamps
            self._requests[identifier] = [
                ts for ts in self._requests[identifier]
                if ts > window_start
            ]
            
            # Check if limit exceeded
            current_count = len(self._requests[identifier])
            
            if current_count >= self.requests_per_window:
                self._blocked_requests += 1
                
                # Calculate retry after
                oldest_in_window = min(self._requests[identifier])
                retry_after = int(oldest_in_window + self.window_seconds - now) + 1
                
                return False, max(1, retry_after)
            
            # Allow request and record timestamp
            self._requests[identifier].append(now)
            return True, 0
    
    def get_remaining(self, identifier: str) -> int:
        """
        Get remaining requests for an identifier.
        
        Args:
            identifier: Unique identifier (usually IP address)
            
        Returns:
            Number of remaining requests in current window
        """
        now = time.time()
        window_start = now - self.window_seconds
        
        with self._lock:
            current_count = len([
                ts for ts in self._requests[identifier]
                if ts > window_start
            ])
            return max(0, self.requests_per_window - current_count)
    
    def reset(self, identifier: str) -> None:
        """Reset rate limit for an identifier."""
        with self._lock:
            self._requests[identifier] = []
    
    def cleanup(self) -> int:
        """
        Clean up expired entries.
        
        Returns:
            Number of entries cleaned up
        """
        now = time.time()
        window_start = now - self.window_seconds
        cleaned = 0
        
        with self._lock:
            for identifier in list(self._requests.keys()):
                old_len = len(self._requests[identifier])
                self._requests[identifier] = [
                    ts for ts in self._requests[identifier]
                    if ts > window_start
                ]
                cleaned += old_len - len(self._requests[identifier])
                
                # Remove empty entries
                if not self._requests[identifier]:
                    del self._requests[identifier]
        
        return cleaned
    
    def stats(self) -> Dict:
        """Get rate limiter statistics."""
        with self._lock:
            return {
                "total_requests": self._total_requests,
                "blocked_requests": self._blocked_requests,
                "unique_ips": len(self._requests),
                "requests_per_window": self.requests_per_window,
                "window_seconds": self.window_seconds
            }


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.
    
    Limits requests per IP address using sliding window algorithm.
    """
    
    # Paths to exclude from rate limiting
    EXCLUDED_PATHS = ["/healthz", "/metrics", "/docs", "/redoc", "/openapi.json"]
    
    def __init__(
        self,
        app,
        requests_per_window: int = None,
        window_seconds: int = None,
        excluded_paths: List[str] = None
    ):
        super().__init__(app)
        self.limiter = SlidingWindowRateLimiter(requests_per_window, window_seconds)
        self.excluded_paths = excluded_paths or self.EXCLUDED_PATHS
        
        logger.info("Rate limiter middleware initialized")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        # Skip rate limiting for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Check rate limit
        is_allowed, retry_after = self.limiter.is_allowed(client_ip)
        
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Rate limit exceeded. Try again in {retry_after} seconds."
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.limiter.requests_per_window),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + retry_after)
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self.limiter.get_remaining(client_ip)
        response.headers["X-RateLimit-Limit"] = str(self.limiter.requests_per_window)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Get the client IP address from the request.
        
        Handles X-Forwarded-For header for requests behind proxies.
        """
        # Check for proxy headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get the first IP in the chain (original client)
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct client
        if request.client:
            return request.client.host
        
        return "unknown"


# Global rate limiter instance
_rate_limiter: SlidingWindowRateLimiter = None


def get_rate_limiter() -> SlidingWindowRateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = SlidingWindowRateLimiter()
    return _rate_limiter


def init_rate_limiter(
    requests_per_window: int = None,
    window_seconds: int = None
) -> SlidingWindowRateLimiter:
    """Initialize the global rate limiter."""
    global _rate_limiter
    _rate_limiter = SlidingWindowRateLimiter(requests_per_window, window_seconds)
    return _rate_limiter
