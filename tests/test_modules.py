"""
Unit tests for the Weather API modules.

Run with: pytest tests/ -v
"""

import pytest
import time
import threading
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock


# ==================== CACHE TESTS ====================

class TestCache:
    """Tests for the cache module."""
    
    def test_cache_set_and_get(self):
        """Test basic set and get operations."""
        from cache import Cache
        
        cache = Cache(default_ttl=60, max_size=100, cleanup_interval=300)
        
        try:
            cache.set("test_key", "test_value")
            result = cache.get("test_key")
            
            assert result == "test_value"
        finally:
            cache.shutdown()
    
    def test_cache_expiration(self):
        """Test that cached items expire after TTL."""
        from cache import Cache
        
        cache = Cache(default_ttl=1, max_size=100, cleanup_interval=300)
        
        try:
            cache.set("expiring_key", "value", ttl=1)
            
            # Should exist immediately
            assert cache.get("expiring_key") == "value"
            
            # Wait for expiration
            time.sleep(1.5)
            
            # Should be expired
            assert cache.get("expiring_key") is None
        finally:
            cache.shutdown()
    
    def test_cache_delete(self):
        """Test delete operation."""
        from cache import Cache
        
        cache = Cache(default_ttl=60, max_size=100, cleanup_interval=300)
        
        try:
            cache.set("delete_key", "value")
            assert cache.get("delete_key") == "value"
            
            result = cache.delete("delete_key")
            assert result is True
            assert cache.get("delete_key") is None
            
            # Deleting non-existent key
            result = cache.delete("non_existent")
            assert result is False
        finally:
            cache.shutdown()
    
    def test_cache_keys(self):
        """Test keys listing."""
        from cache import Cache
        
        cache = Cache(default_ttl=60, max_size=100, cleanup_interval=300)
        
        try:
            cache.set("prefix:key1", "value1")
            cache.set("prefix:key2", "value2")
            cache.set("other:key3", "value3")
            
            all_keys = cache.keys()
            assert len(all_keys) == 3
            
            prefix_keys = cache.keys("prefix:")
            assert len(prefix_keys) == 2
            assert "prefix:key1" in prefix_keys
            assert "prefix:key2" in prefix_keys
        finally:
            cache.shutdown()
    
    def test_cache_stats(self):
        """Test statistics tracking."""
        from cache import Cache
        
        cache = Cache(default_ttl=60, max_size=100, cleanup_interval=300)
        
        try:
            cache.set("stats_key", "value")
            cache.get("stats_key")  # Hit
            cache.get("stats_key")  # Hit
            cache.get("non_existent")  # Miss
            
            stats = cache.stats()
            
            assert stats["hits"] == 2
            assert stats["misses"] == 1
            assert stats["size"] == 1
        finally:
            cache.shutdown()
    
    def test_cache_thread_safety(self):
        """Test thread safety of cache operations."""
        from cache import Cache
        
        cache = Cache(default_ttl=60, max_size=1000, cleanup_interval=300)
        errors = []
        
        try:
            def writer():
                for i in range(100):
                    try:
                        cache.set(f"thread_key_{i}", f"value_{i}")
                    except Exception as e:
                        errors.append(e)
            
            def reader():
                for i in range(100):
                    try:
                        cache.get(f"thread_key_{i}")
                    except Exception as e:
                        errors.append(e)
            
            threads = []
            for _ in range(5):
                threads.append(threading.Thread(target=writer))
                threads.append(threading.Thread(target=reader))
            
            for t in threads:
                t.start()
            
            for t in threads:
                t.join()
            
            assert len(errors) == 0
        finally:
            cache.shutdown()
    
    def test_generate_weather_cache_key(self):
        """Test weather cache key generation."""
        from cache import generate_weather_cache_key
        
        key1 = generate_weather_cache_key(40.7128, -74.0060, "current")
        key2 = generate_weather_cache_key(40.7129, -74.0061, "current")  # Slightly different
        
        # Should be the same due to rounding
        assert key1 == key2
        assert key1 == "weather:current:40.71:-74.01"


# ==================== STORAGE TESTS ====================

class TestStorage:
    """Tests for the storage module."""
    
    @pytest.fixture
    def temp_storage(self, tmp_path):
        """Create a temporary storage instance."""
        from storage import CSVStorage
        storage = CSVStorage(str(tmp_path))
        return storage
    
    def test_user_creation(self, temp_storage):
        """Test user creation."""
        from storage import User
        
        user = User.create(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_pwd"
        )
        
        created = temp_storage.create_user(user)
        
        assert created.user_id is not None
        assert created.username == "testuser"
        assert created.email == "test@example.com"
    
    def test_user_duplicate_email(self, temp_storage):
        """Test duplicate email prevention."""
        from storage import User
        
        user1 = User.create("user1", "same@example.com", "pwd1")
        temp_storage.create_user(user1)
        
        user2 = User.create("user2", "same@example.com", "pwd2")
        
        with pytest.raises(ValueError):
            temp_storage.create_user(user2)
    
    def test_user_retrieval(self, temp_storage):
        """Test user retrieval by different fields."""
        from storage import User
        
        user = User.create("findme", "find@example.com", "pwd")
        temp_storage.create_user(user)
        
        by_id = temp_storage.get_user_by_id(user.user_id)
        by_email = temp_storage.get_user_by_email("find@example.com")
        by_username = temp_storage.get_user_by_username("findme")
        
        assert by_id.user_id == user.user_id
        assert by_email.email == "find@example.com"
        assert by_username.username == "findme"
    
    def test_session_lifecycle(self, temp_storage):
        """Test session creation, retrieval, and invalidation."""
        from storage import Session
        
        session = Session.create("user123", ttl_seconds=3600)
        temp_storage.create_session(session)
        
        retrieved = temp_storage.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.user_id == "user123"
        assert retrieved.is_valid is True
        
        # Invalidate
        temp_storage.invalidate_session(session.session_id)
        
        retrieved = temp_storage.get_session(session.session_id)
        assert retrieved.is_valid is False
    
    def test_search_history(self, temp_storage):
        """Test search history operations."""
        from storage import SearchHistory
        
        entry1 = SearchHistory.create("user1", "New York", 40.71, -74.01)
        entry2 = SearchHistory.create("user1", "London", 51.51, -0.13)
        entry3 = SearchHistory.create("user2", "Paris", 48.86, 2.35)
        
        temp_storage.add_search_history(entry1)
        temp_storage.add_search_history(entry2)
        temp_storage.add_search_history(entry3)
        
        user1_history = temp_storage.get_user_search_history("user1")
        
        assert len(user1_history) == 2
    
    def test_storage_writable(self, temp_storage):
        """Test storage writability check."""
        assert temp_storage.is_writable() is True
    
    def test_storage_stats(self, temp_storage):
        """Test storage statistics."""
        stats = temp_storage.get_stats()
        
        assert "users_count" in stats
        assert "sessions_count" in stats
        assert "is_writable" in stats


# ==================== RATE LIMITER TESTS ====================

class TestRateLimiter:
    """Tests for the rate limiter."""
    
    def test_allows_within_limit(self):
        """Test that requests within limit are allowed."""
        from middleware.rate_limiter import SlidingWindowRateLimiter
        
        limiter = SlidingWindowRateLimiter(requests_per_window=10, window_seconds=60)
        
        for _ in range(10):
            is_allowed, _ = limiter.is_allowed("test_ip")
            assert is_allowed is True
    
    def test_blocks_over_limit(self):
        """Test that requests over limit are blocked."""
        from middleware.rate_limiter import SlidingWindowRateLimiter
        
        limiter = SlidingWindowRateLimiter(requests_per_window=5, window_seconds=60)
        
        # Use up the limit
        for _ in range(5):
            limiter.is_allowed("test_ip")
        
        # This should be blocked
        is_allowed, retry_after = limiter.is_allowed("test_ip")
        
        assert is_allowed is False
        assert retry_after > 0
    
    def test_different_ips_independent(self):
        """Test that different IPs have independent limits."""
        from middleware.rate_limiter import SlidingWindowRateLimiter
        
        limiter = SlidingWindowRateLimiter(requests_per_window=2, window_seconds=60)
        
        # IP1 uses up limit
        limiter.is_allowed("ip1")
        limiter.is_allowed("ip1")
        is_allowed, _ = limiter.is_allowed("ip1")
        assert is_allowed is False
        
        # IP2 should still be allowed
        is_allowed, _ = limiter.is_allowed("ip2")
        assert is_allowed is True
    
    def test_window_sliding(self):
        """Test that window slides properly."""
        from middleware.rate_limiter import SlidingWindowRateLimiter
        
        limiter = SlidingWindowRateLimiter(requests_per_window=2, window_seconds=1)
        
        # Use up limit
        limiter.is_allowed("test_ip")
        limiter.is_allowed("test_ip")
        
        # Should be blocked
        is_allowed, _ = limiter.is_allowed("test_ip")
        assert is_allowed is False
        
        # Wait for window to slide
        time.sleep(1.1)
        
        # Should be allowed again
        is_allowed, _ = limiter.is_allowed("test_ip")
        assert is_allowed is True
    
    def test_stats(self):
        """Test rate limiter statistics."""
        from middleware.rate_limiter import SlidingWindowRateLimiter
        
        limiter = SlidingWindowRateLimiter(requests_per_window=10, window_seconds=60)
        
        limiter.is_allowed("ip1")
        limiter.is_allowed("ip2")
        
        stats = limiter.stats()
        
        assert stats["total_requests"] == 2
        assert stats["unique_ips"] == 2


# ==================== SESSION MIDDLEWARE TESTS ====================

class TestSessionMiddleware:
    """Tests for the session middleware."""
    
    def test_session_data_creation(self):
        """Test SessionData creation."""
        from session_middleware import SessionData
        
        session_data = SessionData()
        
        assert session_data.is_authenticated is False
        assert session_data.user_id is None
    
    def test_session_data_authenticated(self):
        """Test authenticated SessionData."""
        from session_middleware import SessionData
        from storage import Session
        
        session = Session.create("user123")
        session_data = SessionData(
            session=session,
            user_id="user123",
            is_authenticated=True
        )
        
        assert session_data.is_authenticated is True
        assert session_data.user_id == "user123"


# ==================== AUTH ROUTE TESTS ====================

class TestAuthRoutes:
    """Tests for authentication routes."""
    
    def test_password_hashing(self):
        """Test password hashing and verification."""
        from routes.auth import hash_password, verify_password
        
        password = "TestPassword123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False


# ==================== METRICS TESTS ====================

class TestMetrics:
    """Tests for the metrics module."""
    
    def test_increment_counter(self):
        """Test counter increment."""
        from metrics import Metrics
        
        metrics = Metrics()
        
        metrics.increment("total_requests")
        metrics.increment("total_requests")
        metrics.increment("total_requests", 3)
        
        assert metrics.get("total_requests") == 5
    
    def test_get_all_counters(self):
        """Test getting all counters."""
        from metrics import Metrics
        
        metrics = Metrics()
        
        metrics.increment("cache_hits", 10)
        metrics.increment("cache_misses", 5)
        
        all_counters = metrics.get_all()
        
        assert all_counters["cache_hits"] == 10
        assert all_counters["cache_misses"] == 5
    
    def test_uptime(self):
        """Test uptime tracking."""
        from metrics import Metrics
        
        metrics = Metrics()
        
        time.sleep(0.1)
        uptime = metrics.uptime_seconds()
        
        assert uptime >= 0.1


# ==================== CONFIG TESTS ====================

class TestConfig:
    """Tests for the configuration module."""
    
    def test_default_values(self):
        """Test that default values are set."""
        from config import Settings
        
        settings = Settings()
        
        assert settings.APP_NAME == "IntelliWeather"
        assert settings.CACHE_TTL_SECONDS > 0
        assert settings.RATE_LIMIT_PER_MIN > 0
    
    def test_parse_popular_locations(self):
        """Test parsing of popular locations."""
        from config import Settings
        
        settings = Settings()
        locations = settings.parse_popular_locations()
        
        assert len(locations) > 0
        assert "lat" in locations[0]
        assert "lon" in locations[0]
        assert "name" in locations[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
