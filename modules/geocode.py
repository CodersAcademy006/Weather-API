"""
Geocoding Service Module

Provides geocoding and reverse geocoding functionality with caching.
Uses Open-Meteo Geocoding API.
"""

import requests
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import hashlib

from config import settings
from logging_config import get_logger
from cache import get_cache

logger = get_logger(__name__)


class GeocodingService:
    """
    Service for geocoding and reverse geocoding operations.
    
    Features:
    - Forward geocoding (city name -> coordinates)
    - Reverse geocoding (coordinates -> city name)
    - Caching with configurable TTL
    - Normalization and deduplication of results
    """
    
    def __init__(self):
        """Initialize the geocoding service."""
        self._api_url = settings.GEOCODING_API_URL
        self._cache_ttl = settings.GEOCODE_CACHE_TTL_SECONDS
        self._timeout = 10
        logger.info("Geocoding service initialized")
    
    def _generate_cache_key(self, query_type: str, **params) -> str:
        """Generate a cache key for geocoding queries."""
        param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        hash_str = hashlib.md5(param_str.encode()).hexdigest()[:8]
        return f"geocode:{query_type}:{hash_str}"
    
    def _normalize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a geocoding result."""
        return {
            "id": result.get("id", 0),
            "name": result.get("name", ""),
            "latitude": round(result.get("latitude", 0), 4),
            "longitude": round(result.get("longitude", 0), 4),
            "country": result.get("country", ""),
            "country_code": result.get("country_code"),
            "admin1": result.get("admin1"),  # State/Province
            "admin2": result.get("admin2"),  # County/District
            "timezone": result.get("timezone"),
            "population": result.get("population"),
            "elevation": result.get("elevation"),
            "feature_code": result.get("feature_code"),
        }
    
    def _dedupe_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate results based on coordinates."""
        seen = set()
        unique = []
        
        for r in results:
            key = (round(r["latitude"], 2), round(r["longitude"], 2))
            if key not in seen:
                seen.add(key)
                unique.append(r)
        
        return unique
    
    def search(
        self,
        query: str,
        limit: int = 5,
        lang: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for locations by name.
        
        Args:
            query: Search query (city name, etc.)
            limit: Maximum number of results
            lang: Language for results
            
        Returns:
            Dict with results, query, count, and source
        """
        cache = get_cache()
        cache_key = self._generate_cache_key("search", q=query.lower(), limit=limit)
        
        # Check cache
        cached = cache.get(cache_key)
        if cached:
            logger.info(f"GEOCODE CACHE HIT for query: {query}")
            return {**cached, "source": "cache"}
        
        # Fetch from API
        logger.info(f"GEOCODE CACHE MISS for query: {query}. Fetching from API...")
        
        try:
            params = {
                "name": query,
                "count": min(limit * 2, 20),  # Fetch extra for deduplication
                "format": "json"
            }
            if lang:
                params["language"] = lang
            
            response = requests.get(
                self._api_url,
                params=params,
                timeout=self._timeout
            )
            
            if response.status_code != 200:
                logger.error(f"Geocoding API error: {response.status_code}")
                return {
                    "results": [],
                    "query": query,
                    "count": 0,
                    "source": "error"
                }
            
            data = response.json()
            raw_results = data.get("results", [])
            
            # Normalize and dedupe
            normalized = [self._normalize_result(r) for r in raw_results]
            deduped = self._dedupe_results(normalized)[:limit]
            
            result = {
                "results": deduped,
                "query": query,
                "count": len(deduped)
            }
            
            # Cache the result
            cache.set(cache_key, result, ttl=self._cache_ttl)
            
            return {**result, "source": "live"}
            
        except requests.exceptions.Timeout:
            logger.error(f"Geocoding API timeout for query: {query}")
            return {
                "results": [],
                "query": query,
                "count": 0,
                "source": "timeout"
            }
        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return {
                "results": [],
                "query": query,
                "count": 0,
                "source": "error"
            }
    
    def reverse(
        self,
        lat: float,
        lon: float
    ) -> Dict[str, Any]:
        """
        Reverse geocode coordinates to a location.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Dict with location info and source
        """
        # Round coordinates for caching
        lat_rounded = round(lat, 2)
        lon_rounded = round(lon, 2)
        
        cache = get_cache()
        cache_key = self._generate_cache_key("reverse", lat=lat_rounded, lon=lon_rounded)
        
        # Check cache
        cached = cache.get(cache_key)
        if cached:
            logger.info(f"REVERSE GEOCODE CACHE HIT for: {lat_rounded}, {lon_rounded}")
            return {**cached, "source": "cache"}
        
        # For reverse geocoding, we search nearby and find closest
        logger.info(f"REVERSE GEOCODE CACHE MISS for: {lat_rounded}, {lon_rounded}")
        
        try:
            # Use a search with coordinates - Open-Meteo doesn't have direct reverse
            # So we'll search for nearby locations
            params = {
                "name": f"{lat},{lon}",  # This won't work directly
                "count": 1,
                "format": "json"
            }
            
            # Alternative: Use a different approach with the forecast API
            # to get timezone/location info
            forecast_url = settings.OPEN_METEO_API_URL
            forecast_params = {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m",
                "timezone": "auto"
            }
            
            response = requests.get(
                forecast_url,
                params=forecast_params,
                timeout=self._timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                location = {
                    "id": 0,
                    "name": f"Location at {lat_rounded}, {lon_rounded}",
                    "latitude": lat_rounded,
                    "longitude": lon_rounded,
                    "country": "",
                    "country_code": None,
                    "admin1": None,
                    "admin2": None,
                    "timezone": data.get("timezone"),
                    "population": None,
                    "elevation": data.get("elevation"),
                    "feature_code": None
                }
                
                result = {
                    "location": location,
                    "latitude": lat,
                    "longitude": lon
                }
                
                cache.set(cache_key, result, ttl=self._cache_ttl)
                return {**result, "source": "live"}
            
            return {
                "location": None,
                "latitude": lat,
                "longitude": lon,
                "source": "error"
            }
            
        except Exception as e:
            logger.error(f"Reverse geocoding error: {e}")
            return {
                "location": None,
                "latitude": lat,
                "longitude": lon,
                "source": "error"
            }


# Global service instance
_geocoding_service: Optional[GeocodingService] = None


def get_geocoding_service() -> GeocodingService:
    """Get the global geocoding service instance."""
    global _geocoding_service
    if _geocoding_service is None:
        _geocoding_service = GeocodingService()
    return _geocoding_service
