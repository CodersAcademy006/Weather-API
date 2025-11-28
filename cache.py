"""
In-Memory Cache System with TTL

This module provides a thread-safe caching system with:
- Configurable TTL (Time To Live)
- Background cleanup thread for expired keys
- Optional persistence of popular items to CSV storage
- Integration with weather API endpoints
"""

import threading
import time
from typing import Any, Optional, Dict, List, Callable
from dataclasses import dataclass
from datetime import datetime
from config import settings
from logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """Represents a single cache entry with metadata."""
    value: Any
    created_at: float
    expires_at: float
    hits: int = 0
    
    def is_expired(self) -> bool:
        """Check if this cache entry has expired."""
        return time.time() > self.expires_at
    
    def time_remaining(self) -> float:
        """Get remaining TTL in seconds."""
        return max(0, self.expires_at - time.time())


class Cache:
    """
    Thread-safe in-memory cache with TTL support.
    
    Features:
    - get, set, delete, keys operations
    - Background cleanup thread
    - Hit/miss statistics
    - Size limits
    - Optional persistence callbacks
    """
    
    def __init__(
        self,
        default_ttl: int = None,
        max_size: int = None,
        cleanup_interval: int = None
    ):
        """
        Initialize the cache.
        
        Args:
            default_ttl: Default TTL in seconds
            max_size: Maximum number of items to store
            cleanup_interval: Interval between cleanup runs in seconds
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._default_ttl = default_ttl or settings.CACHE_TTL_SECONDS
        self._max_size = max_size or settings.CACHE_MAX_SIZE
        self._cleanup_interval = cleanup_interval or settings.CACHE_CLEANUP_INTERVAL
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        
        # Persistence callback
        self._persist_callback: Optional[Callable[[str, Any], None]] = None
        
        # Start background cleanup thread
        self._cleanup_thread: Optional[threading.Thread] = None
        self._stop_cleanup = threading.Event()
        self._start_cleanup_thread()
        
        logger.info(
            f"Cache initialized with TTL={self._default_ttl}s, "
            f"max_size={self._max_size}, cleanup_interval={self._cleanup_interval}s"
        )
    
    def _start_cleanup_thread(self) -> None:
        """Start the background cleanup thread."""
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
            name="cache-cleanup"
        )
        self._cleanup_thread.start()
    
    def _cleanup_loop(self) -> None:
        """Background loop that periodically cleans up expired entries."""
        while not self._stop_cleanup.wait(self._cleanup_interval):
            self.cleanup_expired()
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from the cache.
        
        Returns:
            Number of entries removed
        """
        removed = 0
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            for key in expired_keys:
                del self._cache[key]
                removed += 1
                
        if removed > 0:
            logger.debug(f"Cleaned up {removed} expired cache entries")
            
        return removed
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            The cached value, or None if not found or expired
        """
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._misses += 1
                return None
                
            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return None
                
            entry.hits += 1
            self._hits += 1
            return entry.value
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: The cache key
            value: The value to cache
            ttl: Optional TTL in seconds (uses default if not specified)
        """
        ttl = ttl if ttl is not None else self._default_ttl
        now = time.time()
        
        with self._lock:
            # Check if we need to evict entries
            if len(self._cache) >= self._max_size and key not in self._cache:
                self._evict_lru()
            
            self._cache[key] = CacheEntry(
                value=value,
                created_at=now,
                expires_at=now + ttl
            )
            
        logger.debug(f"Cache set: {key} (TTL={ttl}s)")
    
    def delete(self, key: str) -> bool:
        """
        Delete a key from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            True if the key was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache delete: {key}")
                return True
            return False
    
    def keys(self, pattern: Optional[str] = None) -> List[str]:
        """
        Get all keys in the cache, optionally filtered by pattern.
        
        Args:
            pattern: Optional prefix pattern to filter keys
            
        Returns:
            List of matching keys
        """
        with self._lock:
            all_keys = list(self._cache.keys())
            if pattern:
                return [k for k in all_keys if k.startswith(pattern)]
            return all_keys
    
    def clear(self) -> None:
        """Clear all entries from the cache."""
        with self._lock:
            self._cache.clear()
        logger.info("Cache cleared")
    
    def size(self) -> int:
        """Get the number of entries in the cache."""
        with self._lock:
            return len(self._cache)
    
    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_percent": round(hit_rate, 2),
                "evictions": self._evictions,
                "default_ttl": self._default_ttl
            }
    
    def _evict_lru(self) -> None:
        """Evict the least recently used entry."""
        if not self._cache:
            return
            
        # Find entry with lowest hit count (simple LRU approximation)
        lru_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].hits
        )
        
        # Persist popular items before eviction
        entry = self._cache[lru_key]
        if entry.hits >= 5 and self._persist_callback:
            try:
                self._persist_callback(lru_key, entry.value)
            except Exception as e:
                logger.error(f"Failed to persist cache entry: {e}")
        
        del self._cache[lru_key]
        self._evictions += 1
        logger.debug(f"Evicted cache entry: {lru_key}")
    
    def set_persist_callback(
        self,
        callback: Callable[[str, Any], None]
    ) -> None:
        """
        Set a callback for persisting popular cache entries.
        
        Args:
            callback: Function that takes (key, value) and persists them
        """
        self._persist_callback = callback
    
    def shutdown(self) -> None:
        """Shutdown the cache and cleanup thread."""
        self._stop_cleanup.set()
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
        logger.info("Cache shutdown complete")


def generate_weather_cache_key(lat: float, lon: float, data_type: str = "current") -> str:
    """
    Generate a cache key for weather data.
    
    Args:
        lat: Latitude (rounded to 2 decimal places)
        lon: Longitude (rounded to 2 decimal places)
        data_type: Type of weather data (current, hourly, daily, aqi)
        
    Returns:
        Cache key string
    """
    # Round to 2 decimal places for ~1km precision
    lat_rounded = round(lat, 2)
    lon_rounded = round(lon, 2)
    return f"weather:{data_type}:{lat_rounded}:{lon_rounded}"


# Global cache instance
_cache: Optional[Cache] = None


def get_cache() -> Cache:
    """
    Get the global cache instance.
    
    Returns:
        The global Cache instance
    """
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache


def init_cache() -> Cache:
    """
    Initialize (or reinitialize) the global cache.
    
    Returns:
        The new Cache instance
    """
    global _cache
    if _cache:
        _cache.shutdown()
    _cache = Cache()
    return _cache
