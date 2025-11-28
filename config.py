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
    APP_VERSION: str = "2.0.0"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = False
    
    # Data storage
    DATA_DIR: str = "data"
    
    # Cache settings
    CACHE_TTL_SECONDS: int = 3600  # 1 hour default
    CACHE_MAX_SIZE: int = 1000  # Maximum number of cached items
    CACHE_CLEANUP_INTERVAL: int = 300  # 5 minutes
    GEOCODE_CACHE_TTL_SECONDS: int = 86400  # 24 hours for geocoding
    
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
    OPEN_METEO_HISTORICAL_URL: str = "https://archive-api.open-meteo.com/v1/archive"
    GEOCODING_API_URL: str = "https://geocoding-api.open-meteo.com/v1/search"
    
    # Popular locations to pre-cache (lat, lon, name)
    POPULAR_LOCATIONS: List[str] = [
        "40.7128,-74.0060,New York",
        "51.5074,-0.1278,London",
        "35.6762,139.6503,Tokyo",
        "48.8566,2.3522,Paris",
        "28.6139,77.2090,New Delhi",
        "31.5204,74.3587,Lahore",
        "24.8607,67.0011,Karachi",
        "19.0760,72.8777,Mumbai",
        "40.4168,-3.7038,Madrid",
        "25.2048,55.2708,Dubai"
    ]
    
    # Observability
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # Options: "json", "text"
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    
    # ==================== PHASE 2 FEATURE FLAGS ====================
    
    # Feature toggles (all disabled by default for safety)
    FEATURE_WEATHER_V2: bool = True  # Hourly/daily/historical endpoints
    FEATURE_GEOCODING: bool = True  # Geocoding endpoints
    FEATURE_ALERTS: bool = True  # Weather alerts
    FEATURE_DOWNLOADS: bool = True  # PDF/Excel downloads
    FEATURE_ADMIN_DASHBOARD: bool = True  # Admin analytics
    FEATURE_DARK_MODE: bool = True  # Frontend dark mode
    FEATURE_I18N: bool = True  # Multi-language support
    FEATURE_API_KEYS: bool = True  # API key management
    FEATURE_ML_PREDICTION: bool = True  # ML temperature prediction
    
    # Alerts configuration
    ALERTS_PREFETCH_INTERVAL_HOURS: int = 6
    ALERTS_ENABLED: bool = True
    
    # Download/Reports configuration
    REPORTS_CACHE_TTL_SECONDS: int = 1800  # 30 minutes
    REPORTS_MAX_DAYS: int = 30
    
    # API Keys configuration
    API_KEY_RATE_LIMIT_DEFAULT: int = 100  # Requests per minute per key
    API_KEY_ENABLED: bool = True
    
    # ML Prediction configuration
    ML_MODEL_RETRAIN_HOURS: int = 24
    ML_HISTORICAL_DAYS: int = 365
    
    # i18n configuration
    DEFAULT_LANGUAGE: str = "en"
    SUPPORTED_LANGUAGES: List[str] = ["en", "hi", "ur", "ar", "es"]
    
    # Admin configuration
    ADMIN_EMAILS: List[str] = []  # List of admin email addresses
    
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
    
    def is_admin(self, email: str) -> bool:
        """Check if an email is an admin."""
        return email.lower() in [e.lower() for e in self.ADMIN_EMAILS]


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
