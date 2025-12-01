"""
Model Training Worker

Background worker for retraining the ML prediction model.
"""

import threading
import time
from datetime import datetime, timezone
from typing import Optional

from config import settings
from logging_config import get_logger
from modules.prediction import get_prediction_service

logger = get_logger(__name__)


class ModelTrainer:
    """
    Background worker for periodic model retraining.
    
    Retrains the prediction model on a schedule to keep it up-to-date
    with recent weather patterns.
    """
    
    def __init__(self, interval_hours: int = None):
        """
        Initialize the model trainer.
        
        Args:
            interval_hours: Retrain interval in hours
        """
        self._interval = (interval_hours or settings.ML_MODEL_RETRAIN_HOURS) * 3600
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_train: Optional[datetime] = None
        self._train_success = False
        
        logger.info(f"Model trainer initialized with {self._interval / 3600}h interval")
    
    def start(self) -> None:
        """Start the background trainer."""
        if self._thread and self._thread.is_alive():
            logger.warning("Trainer already running")
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="model-trainer"
        )
        self._thread.start()
        logger.info("Model trainer started")
    
    def stop(self) -> None:
        """Stop the background trainer."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=30)
        logger.info("Model trainer stopped")
    
    def _run_loop(self) -> None:
        """Main training loop."""
        # Initial training with a default location
        self._train_default()
        
        while not self._stop_event.wait(self._interval):
            self._train_default()
    
    def _train_default(self) -> None:
        """Train model with data from a popular location."""
        locations = settings.parse_popular_locations()
        
        if not locations:
            logger.warning("No popular locations configured for training")
            return
        
        # Use first location for training
        loc = locations[0]
        
        logger.info(f"Starting model training with data from {loc['name']}")
        
        try:
            prediction_service = get_prediction_service()
            success = prediction_service.train_model(loc["lat"], loc["lon"])
            
            self._last_train = datetime.now(timezone.utc)
            self._train_success = success
            
            if success:
                logger.info("Model training completed successfully")
            else:
                logger.warning("Model training failed")
                
        except Exception as e:
            logger.error(f"Model training error: {e}")
            self._train_success = False
    
    def trigger_train(self, lat: float, lon: float) -> dict:
        """Manually trigger training for a specific location."""
        try:
            prediction_service = get_prediction_service()
            success = prediction_service.train_model(lat, lon)
            
            self._last_train = datetime.now(timezone.utc)
            self._train_success = success
            
            return {
                "success": success,
                "trained_at": self._last_train.isoformat(),
                "location": f"{lat}, {lon}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_status(self) -> dict:
        """Get trainer status."""
        return {
            "running": self._thread.is_alive() if self._thread else False,
            "last_train": self._last_train.isoformat() if self._last_train else None,
            "last_success": self._train_success,
            "interval_hours": self._interval / 3600
        }


# Global trainer instance
_trainer: Optional[ModelTrainer] = None


def get_model_trainer() -> Optional[ModelTrainer]:
    """Get the global model trainer instance."""
    return _trainer


def init_model_trainer() -> ModelTrainer:
    """Initialize the global model trainer."""
    global _trainer
    
    if _trainer:
        _trainer.stop()
    
    _trainer = ModelTrainer()
    return _trainer
