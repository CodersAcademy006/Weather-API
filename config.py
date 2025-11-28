"""
Centralized Configuration Module

This module provides a unified configuration system using Pydantic BaseSettings.
All configuration values can be overridden via environment variables.
"""

import os
from typing import List, Optional
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings have sensible defaults for development but should be
    overridden in production via environment variables.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application settings
    APP_NAME: str = "IntelliWeather"
    APP_VERSION: str = "1.0.0"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = False
    
    # Data storage
    DATA_DIR: str = "data"
    
    # Cache settings
    CACHE_TTL_SECONDS: int = 3600  # 1 hour default
    CACHE_MAX_SIZE: int = 1000  # Maximum number of cached items
    CACHE_CLEANUP_INTERVAL: int = 300  # 5 minutes
    
    # Session settings
    SESSION_TIMEOUT_SECONDS: int = 86400  # 24 hours
    SESSION_COOKIE_NAME: str = "session_id"
    SESSION_COOKIE_SECURE: bool = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "lax"
    SESSION_BACKEND: str = "csv"  # Options: "csv", "redis"
    
    # Redis settings (for production session backend)
    REDIS_URL: Optional[str] = None
    
    # Rate limiting
    RATE_LIMIT_PER_MIN: int = 60  # Requests per minute per IP
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    
    # Security
    SECRET_KEY: str = "change-this-in-production-use-a-secure-random-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    DB_CONNECTION_STRING: Optional[str] = None
    
    # External APIs
    OPEN_METEO_API_URL: str = "https://api.open-meteo.com/v1/forecast"
    OPEN_METEO_AIR_QUALITY_URL: str = "https://air-quality-api.open-meteo.com/v1/air-quality"
    GEOCODING_API_URL: str = "https://geocoding-api.open-meteo.com/v1/search"
    
    # Popular locations to pre-cache (lat, lon, name)
    POPULAR_LOCATIONS: List[str] = [
        "40.7128,-74.0060,New York",
        "51.5074,-0.1278,London",
        "35.6762,139.6503,Tokyo",
        "48.8566,2.3522,Paris",
        "28.6139,77.2090,New Delhi"
    ]
    
    # Observability
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # Options: "json", "text"
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    
    def get_data_path(self, filename: str) -> str:
        """Get the full path for a data file."""
        return os.path.join(self.DATA_DIR, filename)
    
    def parse_popular_locations(self) -> List[dict]:
        """Parse popular locations into a list of dictionaries."""
        locations = []
        for loc in self.POPULAR_LOCATIONS:
            parts = loc.split(",")
            if len(parts) >= 3:
                locations.append({
                    "lat": float(parts[0]),
                    "lon": float(parts[1]),
                    "name": ",".join(parts[2:])
                })
        return locations


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    This function is cached to avoid re-reading environment variables
    on every call. Use `get_settings.cache_clear()` to reload settings.
    """
    return Settings()


# Convenience function for accessing settings
settings = get_settings()
