"""
Alerts Prefetcher Worker

Background worker that periodically fetches weather alerts for popular locations.
"""

import threading
import time
from datetime import datetime, timezone
from typing import Optional, Callable

from config import settings
from logging_config import get_logger
from cache import get_cache

logger = get_logger(__name__)


class AlertsPrefetcher:
    """
    Background worker for prefetching weather alerts.
    
    Runs periodically to cache alerts for popular locations,
    ensuring fast response times for common requests.
    """
    
    def __init__(
        self,
        fetch_alerts_func: Callable,
        interval_hours: int = None
    ):
        """
        Initialize the alerts prefetcher.
        
        Args:
            fetch_alerts_func: Function to fetch alerts (lat, lon) -> List[Alert]
            interval_hours: Prefetch interval in hours
        """
        self._fetch_alerts = fetch_alerts_func
        self._interval = (interval_hours or settings.ALERTS_PREFETCH_INTERVAL_HOURS) * 3600
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_run: Optional[datetime] = None
        self._alerts_count = 0
        
        logger.info(f"Alerts prefetcher initialized with {self._interval / 3600}h interval")
    
    def start(self) -> None:
        """Start the background prefetcher."""
        if self._thread and self._thread.is_alive():
            logger.warning("Prefetcher already running")
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="alerts-prefetcher"
        )
        self._thread.start()
        logger.info("Alerts prefetcher started")
    
    def stop(self) -> None:
        """Stop the background prefetcher."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("Alerts prefetcher stopped")
    
    def _run_loop(self) -> None:
        """Main prefetch loop."""
        # Initial prefetch
        self._prefetch_all()
        
        while not self._stop_event.wait(self._interval):
            self._prefetch_all()
    
    def _prefetch_all(self) -> None:
        """Prefetch alerts for all popular locations."""
        locations = settings.parse_popular_locations()
        cache = get_cache()
        
        logger.info(f"Starting alerts prefetch for {len(locations)} locations")
        
        total_alerts = 0
        
        for loc in locations:
            try:
                alerts = self._fetch_alerts(loc["lat"], loc["lon"])
                
                # Cache the alerts
                cache_key = f"alerts:{loc['lat']}:{loc['lon']}"
                cache_data = {
                    "latitude": loc["lat"],
                    "longitude": loc["lon"],
                    "location_name": loc["name"],
                    "alerts": [a.model_dump() if hasattr(a, 'model_dump') else a for a in alerts],
                    "count": len(alerts),
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "source": "prefetch"
                }
                
                cache.set(cache_key, cache_data, ttl=900)  # 15 minutes
                total_alerts += len(alerts)
                
            except Exception as e:
                logger.error(f"Failed to prefetch alerts for {loc['name']}: {e}")
        
        self._last_run = datetime.now(timezone.utc)
        self._alerts_count = total_alerts
        
        logger.info(f"Alerts prefetch complete: {total_alerts} alerts for {len(locations)} locations")
    
    def trigger_refresh(self) -> dict:
        """Manually trigger a refresh."""
        self._prefetch_all()
        return {
            "refreshed_at": self._last_run.isoformat() if self._last_run else None,
            "alerts_count": self._alerts_count
        }
    
    def get_status(self) -> dict:
        """Get prefetcher status."""
        return {
            "running": self._thread.is_alive() if self._thread else False,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "alerts_count": self._alerts_count,
            "interval_hours": self._interval / 3600,
            "locations_count": len(settings.parse_popular_locations())
        }


# Global prefetcher instance
_prefetcher: Optional[AlertsPrefetcher] = None


def get_alerts_prefetcher() -> Optional[AlertsPrefetcher]:
    """Get the global alerts prefetcher instance."""
    return _prefetcher


def init_alerts_prefetcher(fetch_func: Callable) -> AlertsPrefetcher:
    """Initialize the global alerts prefetcher."""
    global _prefetcher
    
    if _prefetcher:
        _prefetcher.stop()
    
    _prefetcher = AlertsPrefetcher(fetch_func)
    return _prefetcher
