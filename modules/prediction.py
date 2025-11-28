"""
ML Prediction Module

Simple machine learning module for next-day temperature prediction.
Uses linear regression on historical data from Open-Meteo.
"""

import os
import json
import pickle
import random
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

import requests

from config import settings
from logging_config import get_logger
from cache import get_cache

logger = get_logger(__name__)


@dataclass
class PredictionResult:
    """Result of a temperature prediction."""
    predicted_temperature: float
    confidence_interval_low: float
    confidence_interval_high: float
    model_version: str
    trained_at: str
    historical_days_used: int
    location: str


class SimplePredictionModel:
    """
    Simple linear regression model for temperature prediction.
    
    Uses historical temperature data to predict next-day temperature.
    Features include: day of year, previous day temps, trend.
    """
    
    def __init__(self):
        """Initialize the model."""
        self.weights: Optional[List[float]] = None
        self.bias: float = 0.0
        self.version: str = "1.0.0"
        self.trained_at: Optional[str] = None
        self.feature_names = ["day_of_year_sin", "day_of_year_cos", "prev_temp", "temp_trend"]
        self._random_seed = 42
    
    def _compute_features(self, data: List[Dict[str, Any]], index: int) -> Optional[List[float]]:
        """
        Compute features for a single data point.
        
        Args:
            data: Historical data list
            index: Index of current data point
            
        Returns:
            List of features or None if not enough data
        """
        import math
        
        if index < 3:  # Need at least 3 previous days
            return None
        
        current = data[index]
        prev1 = data[index - 1]
        prev2 = data[index - 2]
        prev3 = data[index - 3]
        
        # Parse date
        date = datetime.fromisoformat(current["date"])
        day_of_year = date.timetuple().tm_yday
        
        # Cyclical encoding for day of year
        day_sin = math.sin(2 * math.pi * day_of_year / 365)
        day_cos = math.cos(2 * math.pi * day_of_year / 365)
        
        # Previous day temperature (mean)
        prev_temp = (prev1.get("temperature_max", 20) + prev1.get("temperature_min", 10)) / 2
        
        # Temperature trend (difference over 3 days)
        prev1_mean = (prev1.get("temperature_max", 20) + prev1.get("temperature_min", 10)) / 2
        prev3_mean = (prev3.get("temperature_max", 20) + prev3.get("temperature_min", 10)) / 2
        trend = (prev1_mean - prev3_mean) / 2
        
        return [day_sin, day_cos, prev_temp, trend]
    
    def train(self, data: List[Dict[str, Any]]) -> bool:
        """
        Train the model on historical data.
        
        Args:
            data: List of daily weather data with date, temperature_max, temperature_min
            
        Returns:
            True if training successful
        """
        random.seed(self._random_seed)
        
        if len(data) < 30:
            logger.warning("Not enough data for training (need at least 30 days)")
            return False
        
        # Prepare training data
        X = []
        y = []
        
        for i in range(3, len(data) - 1):
            features = self._compute_features(data, i)
            if features:
                X.append(features)
                # Target: next day mean temperature
                next_day = data[i + 1]
                target = (next_day.get("temperature_max", 20) + next_day.get("temperature_min", 10)) / 2
                y.append(target)
        
        if len(X) < 10:
            logger.warning("Not enough valid training samples")
            return False
        
        # Simple gradient descent for linear regression
        n_features = len(self.feature_names)
        self.weights = [0.0] * n_features
        self.bias = sum(y) / len(y)  # Initialize bias to mean
        
        learning_rate = 0.01
        epochs = 100
        
        for _ in range(epochs):
            for xi, yi in zip(X, y):
                # Prediction
                pred = self.bias + sum(w * f for w, f in zip(self.weights, xi))
                
                # Error
                error = pred - yi
                
                # Update weights
                for j in range(n_features):
                    self.weights[j] -= learning_rate * error * xi[j]
                self.bias -= learning_rate * error
        
        self.trained_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Model trained with {len(X)} samples")
        
        return True
    
    def predict(self, features: List[float]) -> Tuple[float, float, float]:
        """
        Make a prediction.
        
        Args:
            features: Input features
            
        Returns:
            Tuple of (prediction, confidence_low, confidence_high)
        """
        if not self.weights:
            raise ValueError("Model not trained")
        
        pred = self.bias + sum(w * f for w, f in zip(self.weights, features))
        
        # Simple confidence interval (±3°C)
        confidence = 3.0
        
        return pred, pred - confidence, pred + confidence
    
    def save(self, filepath: str) -> None:
        """Save model to file."""
        model_data = {
            "weights": self.weights,
            "bias": self.bias,
            "version": self.version,
            "trained_at": self.trained_at,
            "feature_names": self.feature_names
        }
        
        with open(filepath, "w") as f:
            json.dump(model_data, f)
        
        logger.info(f"Model saved to {filepath}")
    
    def load(self, filepath: str) -> bool:
        """Load model from file."""
        if not os.path.exists(filepath):
            return False
        
        try:
            with open(filepath, "r") as f:
                model_data = json.load(f)
            
            self.weights = model_data["weights"]
            self.bias = model_data["bias"]
            self.version = model_data["version"]
            self.trained_at = model_data["trained_at"]
            self.feature_names = model_data["feature_names"]
            
            logger.info(f"Model loaded from {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False


class PredictionService:
    """
    Service for weather predictions.
    
    Features:
    - Train model on historical data
    - Predict next-day temperature
    - Cache predictions
    """
    
    def __init__(self):
        """Initialize the prediction service."""
        self._model = SimplePredictionModel()
        self._model_dir = os.path.join(settings.DATA_DIR, "models")
        self._model_path = os.path.join(self._model_dir, "temp_model.json")
        self._historical_url = settings.OPEN_METEO_HISTORICAL_URL
        
        # Create model directory
        os.makedirs(self._model_dir, exist_ok=True)
        
        # Try to load existing model
        self._model.load(self._model_path)
        
        logger.info("Prediction service initialized")
    
    def _fetch_historical_data(
        self,
        lat: float,
        lon: float,
        days: int = 365
    ) -> Optional[List[Dict[str, Any]]]:
        """Fetch historical weather data."""
        end_date = datetime.now(timezone.utc).date() - timedelta(days=1)
        start_date = end_date - timedelta(days=days)
        
        try:
            params = {
                "latitude": lat,
                "longitude": lon,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "daily": "temperature_2m_max,temperature_2m_min",
                "timezone": "auto"
            }
            
            response = requests.get(
                self._historical_url,
                params=params,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Historical API error: {response.status_code}")
                return None
            
            data = response.json()
            daily = data.get("daily", {})
            
            if not daily.get("time"):
                return None
            
            result = []
            for i, date in enumerate(daily["time"]):
                result.append({
                    "date": date,
                    "temperature_max": daily["temperature_2m_max"][i],
                    "temperature_min": daily["temperature_2m_min"][i]
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to fetch historical data: {e}")
            return None
    
    def train_model(self, lat: float, lon: float) -> bool:
        """
        Train the model on historical data for a location.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            True if training successful
        """
        logger.info(f"Training model for location: {lat}, {lon}")
        
        # Fetch historical data
        data = self._fetch_historical_data(lat, lon, settings.ML_HISTORICAL_DAYS)
        
        if not data:
            logger.error("No historical data available for training")
            return False
        
        # Train model
        success = self._model.train(data)
        
        if success:
            self._model.save(self._model_path)
        
        return success
    
    def predict_next_day(
        self,
        lat: float,
        lon: float
    ) -> Optional[PredictionResult]:
        """
        Predict next day temperature for a location.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            PredictionResult or None if prediction fails
        """
        cache = get_cache()
        cache_key = f"prediction:{round(lat, 2)}:{round(lon, 2)}"
        
        # Check cache
        cached = cache.get(cache_key)
        if cached:
            logger.info(f"PREDICTION CACHE HIT for {lat}, {lon}")
            return PredictionResult(**cached)
        
        # Check if model is trained
        if not self._model.weights:
            # Try to train with recent data
            logger.info("Model not trained, attempting to train...")
            if not self.train_model(lat, lon):
                # Use fallback prediction
                return self._fallback_prediction(lat, lon)
        
        # Fetch recent data for features
        recent_data = self._fetch_historical_data(lat, lon, 7)
        
        if not recent_data or len(recent_data) < 4:
            return self._fallback_prediction(lat, lon)
        
        # Compute features using most recent data
        features = self._model._compute_features(recent_data, len(recent_data) - 1)
        
        if not features:
            return self._fallback_prediction(lat, lon)
        
        # Make prediction
        try:
            pred, low, high = self._model.predict(features)
            
            result = PredictionResult(
                predicted_temperature=round(pred, 1),
                confidence_interval_low=round(low, 1),
                confidence_interval_high=round(high, 1),
                model_version=self._model.version,
                trained_at=self._model.trained_at or datetime.now(timezone.utc).isoformat(),
                historical_days_used=settings.ML_HISTORICAL_DAYS,
                location=f"{lat}, {lon}"
            )
            
            # Cache prediction (1 hour)
            cache.set(cache_key, result.__dict__, ttl=3600)
            
            return result
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return self._fallback_prediction(lat, lon)
    
    def _fallback_prediction(self, lat: float, lon: float) -> PredictionResult:
        """Fallback prediction when model is unavailable."""
        # Use a simple climatological estimate based on latitude
        # Higher latitudes = cooler, lower = warmer
        base_temp = 25 - abs(lat) * 0.5
        
        return PredictionResult(
            predicted_temperature=round(base_temp, 1),
            confidence_interval_low=round(base_temp - 5, 1),
            confidence_interval_high=round(base_temp + 5, 1),
            model_version="fallback",
            trained_at=datetime.now(timezone.utc).isoformat(),
            historical_days_used=0,
            location=f"{lat}, {lon}"
        )
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        return {
            "version": self._model.version,
            "trained_at": self._model.trained_at,
            "is_trained": self._model.weights is not None,
            "feature_names": self._model.feature_names,
            "model_path": self._model_path
        }


# Global service instance
_prediction_service: Optional[PredictionService] = None


def get_prediction_service() -> PredictionService:
    """Get the global prediction service instance."""
    global _prediction_service
    if _prediction_service is None:
        _prediction_service = PredictionService()
    return _prediction_service
