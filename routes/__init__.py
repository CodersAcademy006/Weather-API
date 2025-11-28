"""
Routes package initialization.

Phase 1 Routes:
- auth: Authentication endpoints

Phase 2 Routes:
- weather_v2: Enhanced weather endpoints (hourly, daily, historical)
- geocode: Geocoding and reverse geocoding
- alerts: Weather alerts and warnings
- downloads: PDF/Excel report downloads
- apikeys: API key management
- predict: ML-based predictions
- admin: Admin dashboard and analytics
- i18n: Internationalization
"""

from routes.auth import router as auth_router
from routes.weather_v2 import router as weather_v2_router
from routes.geocode import router as geocode_router
from routes.alerts import router as alerts_router
from routes.downloads import router as downloads_router
from routes.apikeys import router as apikeys_router
from routes.predict import router as predict_router
from routes.admin import router as admin_router
from routes.i18n import router as i18n_router

__all__ = [
    "auth_router",
    "weather_v2_router",
    "geocode_router",
    "alerts_router",
    "downloads_router",
    "apikeys_router",
    "predict_router",
    "admin_router",
    "i18n_router",
]
