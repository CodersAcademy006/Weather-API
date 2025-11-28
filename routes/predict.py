"""
Prediction Routes

Provides ML-based weather prediction endpoints.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from config import settings
from logging_config import get_logger
from metrics import get_metrics
from modules.prediction import get_prediction_service, PredictionResult

logger = get_logger(__name__)

router = APIRouter(
    prefix="/predict",
    tags=["ML Prediction"],
    responses={
        400: {"description": "Bad Request"},
        503: {"description": "Prediction Service Unavailable"}
    }
)


class PredictionResponse(BaseModel):
    """Response model for temperature prediction."""
    predicted_temperature: float = Field(..., description="Predicted temperature in Celsius")
    confidence_interval_low: float = Field(..., description="Lower bound of confidence interval")
    confidence_interval_high: float = Field(..., description="Upper bound of confidence interval")
    model_version: str = Field(..., description="Version of the prediction model")
    trained_at: str = Field(..., description="When the model was last trained")
    historical_days_used: int = Field(..., description="Number of historical days used for training")
    location: str = Field(..., description="Location coordinates")
    generated_at: str = Field(..., description="When this prediction was generated")

    class Config:
        json_schema_extra = {
            "example": {
                "predicted_temperature": 22.5,
                "confidence_interval_low": 19.5,
                "confidence_interval_high": 25.5,
                "model_version": "1.0.0",
                "trained_at": "2024-01-15T00:00:00Z",
                "historical_days_used": 365,
                "location": "40.71, -74.01",
                "generated_at": "2024-01-15T12:00:00Z"
            }
        }


class ModelInfoResponse(BaseModel):
    """Response model for model information."""
    version: str
    trained_at: Optional[str]
    is_trained: bool
    feature_names: list
    model_path: str


@router.get(
    "/nextday",
    response_model=PredictionResponse,
    summary="Predict next-day temperature",
    description="""
    Get a prediction for tomorrow's mean temperature at a location.
    
    **Parameters:**
    - `lat`: Latitude (-90 to 90)
    - `lon`: Longitude (-180 to 180)
    
    **Model Details:**
    - Uses linear regression on historical temperature data
    - Features include: day of year (cyclical), previous temperatures, trend
    - Confidence interval represents ±3°C uncertainty
    
    **Note:** This is a simple demonstration model. For production use,
    consider more sophisticated approaches.
    
    **Example:**
    ```
    curl "https://api.example.com/predict/nextday?lat=40.7128&lon=-74.006"
    ```
    """
)
async def predict_next_day_temperature(
    request: Request,
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude")
):
    """Predict next-day mean temperature for a location."""
    metrics = get_metrics()
    metrics.increment("total_requests")
    metrics.increment("prediction_requests")
    
    prediction_service = get_prediction_service()
    
    result = prediction_service.predict_next_day(lat, lon)
    
    if not result:
        raise HTTPException(
            status_code=503,
            detail="Prediction service temporarily unavailable"
        )
    
    return PredictionResponse(
        predicted_temperature=result.predicted_temperature,
        confidence_interval_low=result.confidence_interval_low,
        confidence_interval_high=result.confidence_interval_high,
        model_version=result.model_version,
        trained_at=result.trained_at,
        historical_days_used=result.historical_days_used,
        location=result.location,
        generated_at=datetime.now(timezone.utc).isoformat()
    )


@router.get(
    "/model/info",
    response_model=ModelInfoResponse,
    summary="Get prediction model information",
    description="Get information about the current prediction model."
)
async def get_model_info(request: Request):
    """Get information about the prediction model."""
    prediction_service = get_prediction_service()
    info = prediction_service.get_model_info()
    
    return ModelInfoResponse(**info)


@router.post(
    "/model/train",
    summary="Train prediction model",
    description="""
    Trigger model training for a specific location.
    
    **Note:** Training uses historical data from Open-Meteo and may take a few seconds.
    """
)
async def train_model(
    request: Request,
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude")
):
    """Train the prediction model for a location."""
    metrics = get_metrics()
    metrics.increment("model_train_requests")
    
    prediction_service = get_prediction_service()
    success = prediction_service.train_model(lat, lon)
    
    if not success:
        raise HTTPException(
            status_code=503,
            detail="Failed to train model. Historical data may be unavailable."
        )
    
    return {
        "message": "Model trained successfully",
        "location": f"{lat}, {lon}",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
