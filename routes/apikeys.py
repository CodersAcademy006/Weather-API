"""
API Keys Routes - Complete LEVEL 3 Implementation

Provides endpoints for API key management with usage tracking.
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Depends, Header
from pydantic import BaseModel, Field

from config import settings
from logging_config import get_logger
from metrics import get_metrics
from session_middleware import require_auth
from modules.api_keys import get_api_key_manager

logger = get_logger(__name__)

router = APIRouter(
    prefix="/apikeys",
    tags=["API Keys"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        429: {"description": "Rate Limited"}
    }
)


# Schemas
class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Descriptive name for the API key")
    expires_in_days: Optional[int] = Field(None, ge=1, le=3650, description="Key expiration in days (optional)")


class APIKeyResponse(BaseModel):
    key_id: str
    name: str
    key_prefix: str
    created_at: str
    expires_at: Optional[str]
    last_used_at: Optional[str]
    is_active: bool
    subscription_tier: str


class APIKeyCreated(BaseModel):
    key_id: str
    name: str
    api_key: str
    created_at: str
    expires_at: Optional[str]
    subscription_tier: str
    warning: str = "Store this key securely. It will not be shown again."


class APIKeyUsageStats(BaseModel):
    key_id: str
    total_requests: int
    successful: int
    failed: int
    success_rate: float
    avg_latency_ms: float
    period_days: int


@router.post("", response_model=APIKeyCreated, summary="Create API Key")
async def create_api_key(
    request: Request,
    key_data: APIKeyCreate,
    user = Depends(require_auth)
):
    """Create a new API key for accessing weather endpoints."""
    metrics = get_metrics()
    metrics.increment("apikey_create_requests")
    
    manager = get_api_key_manager()
    
    # Get user's subscription tier from storage
    from storage import get_storage
    storage = get_storage()
    user_obj = storage.get_user_by_id(user.user_id)
    subscription_tier = user_obj.subscription_tier if user_obj else "free"
    
    api_key, raw_key = manager.create_key(
        user_id=user.user_id,
        name=key_data.name,
        subscription_tier=subscription_tier,
        expires_in_days=key_data.expires_in_days
    )
    
    logger.info(f"Created API key {api_key.key_id} for user {user.user_id}")
    
    return APIKeyCreated(
        key_id=api_key.key_id,
        name=api_key.name,
        api_key=raw_key,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
        subscription_tier=api_key.subscription_tier
    )


@router.get("", response_model=List[APIKeyResponse], summary="List API Keys")
async def list_api_keys(
    request: Request,
    user = Depends(require_auth)
):
    """List all API keys for the authenticated user."""
    metrics = get_metrics()
    metrics.increment("apikey_list_requests")
    
    manager = get_api_key_manager()
    keys = manager.get_user_keys(user.user_id)
    
    return [
        APIKeyResponse(
            key_id=key.key_id,
            name=key.name,
            key_prefix=key.key_prefix,
            created_at=key.created_at,
            expires_at=key.expires_at,
            last_used_at=key.last_used_at,
            is_active=key.is_active,
            subscription_tier=key.subscription_tier
        )
        for key in keys
    ]


@router.delete("/{key_id}", summary="Revoke API Key")
async def revoke_api_key(
    request: Request,
    key_id: str,
    user = Depends(require_auth)
):
    """Revoke an API key."""
    metrics = get_metrics()
    metrics.increment("apikey_revoke_requests")
    
    manager = get_api_key_manager()
    success = manager.revoke_key(key_id, user.user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    
    logger.info(f"Revoked API key {key_id} for user {user.user_id}")
    
    return {"message": "API key revoked successfully", "key_id": key_id}


@router.get("/{key_id}/usage", response_model=APIKeyUsageStats, summary="Get API Key Usage Stats")
async def get_key_usage(
    request: Request,
    key_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    user = Depends(require_auth)
):
    """Get usage statistics for an API key."""
    metrics = get_metrics()
    metrics.increment("apikey_usage_requests")
    
    manager = get_api_key_manager()
    
    # Verify key belongs to user
    keys = manager.get_user_keys(user.user_id)
    if not any(k.key_id == key_id for k in keys):
        raise HTTPException(status_code=404, detail="API key not found")
    
    stats = manager.get_usage_stats(key_id, days)
    
    return APIKeyUsageStats(
        key_id=key_id,
        **stats
    )
