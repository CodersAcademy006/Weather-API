"""
API Keys Routes

Provides endpoints for API key management.
"""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, Query, Request, Depends, Header

from config import settings
from logging_config import get_logger
from metrics import get_metrics
from session_middleware import require_auth, get_session
from modules.api_keys import get_api_key_manager
from schemas.api_keys import (
    APIKeyCreate,
    APIKeyResponse,
    APIKeyCreated,
    APIKeyList
)

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


@router.post(
    "",
    response_model=APIKeyCreated,
    summary="Create a new API key",
    description="""
    Create a new API key for accessing weather endpoints.
    
    **Important:** The full API key is only shown once upon creation.
    Store it securely as it cannot be retrieved later.
    
    **Parameters:**
    - `name`: Descriptive name for the key
    - `rate_limit`: Custom rate limit (requests/min), optional
    - `expires_in_days`: Key expiration in days, optional
    """
)
async def create_api_key(
    request: Request,
    key_data: APIKeyCreate,
    user = Depends(require_auth)
):
    """Create a new API key."""
    metrics = get_metrics()
    metrics.increment("apikey_create_requests")
    
    manager = get_api_key_manager()
    
    api_key, raw_key = manager.create_key(
        user_id=user.user_id,
        name=key_data.name,
        rate_limit=key_data.rate_limit,
        expires_in_days=key_data.expires_in_days
    )
    
    logger.info(f"Created API key {api_key.key_id} for user {user.user_id}")
    
    return APIKeyCreated(
        key_id=api_key.key_id,
        name=api_key.name,
        api_key=raw_key,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
        rate_limit=api_key.rate_limit,
        warning="Store this key securely. It will not be shown again."
    )


@router.get(
    "",
    response_model=APIKeyList,
    summary="List your API keys",
    description="Get a list of all API keys associated with your account."
)
async def list_api_keys(
    request: Request,
    user = Depends(require_auth)
):
    """List all API keys for the authenticated user."""
    metrics = get_metrics()
    metrics.increment("apikey_list_requests")
    
    manager = get_api_key_manager()
    keys = manager.get_user_keys(user.user_id)
    
    key_responses = [
        APIKeyResponse(
            key_id=key.key_id,
            name=key.name,
            key_prefix=key.key_prefix,
            created_at=key.created_at,
            expires_at=key.expires_at,
            last_used_at=key.last_used_at,
            rate_limit=key.rate_limit,
            total_requests=key.total_requests,
            is_active=key.is_active
        )
        for key in keys
    ]
    
    return APIKeyList(
        keys=key_responses,
        count=len(key_responses)
    )


@router.delete(
    "/{key_id}",
    summary="Revoke an API key",
    description="Revoke (deactivate) an API key. This action cannot be undone."
)
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
        raise HTTPException(
            status_code=404,
            detail="API key not found or you don't have permission to revoke it"
        )
    
    logger.info(f"Revoked API key {key_id}")
    
    return {"message": "API key revoked successfully", "key_id": key_id}


@router.get(
    "/{key_id}",
    response_model=APIKeyResponse,
    summary="Get API key details",
    description="Get details about a specific API key."
)
async def get_api_key(
    request: Request,
    key_id: str,
    user = Depends(require_auth)
):
    """Get details about an API key."""
    manager = get_api_key_manager()
    key = manager.get_key_by_id(key_id)
    
    if not key or key.user_id != user.user_id:
        raise HTTPException(
            status_code=404,
            detail="API key not found"
        )
    
    return APIKeyResponse(
        key_id=key.key_id,
        name=key.name,
        key_prefix=key.key_prefix,
        created_at=key.created_at,
        expires_at=key.expires_at,
        last_used_at=key.last_used_at,
        rate_limit=key.rate_limit,
        total_requests=key.total_requests,
        is_active=key.is_active
    )


# Dependency for API key authentication
async def verify_api_key(
    x_api_key: str = Header(None, alias="X-API-Key"),
    apikey: str = Query(None)
):
    """
    Verify API key from header or query parameter.
    
    Usage in routes:
    ```python
    @router.get("/protected")
    async def protected_endpoint(api_key = Depends(verify_api_key)):
        ...
    ```
    """
    key = x_api_key or apikey
    
    if not key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide via X-API-Key header or apikey query parameter."
        )
    
    manager = get_api_key_manager()
    api_key = manager.validate_key(key)
    
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired API key"
        )
    
    # Check rate limit
    allowed, remaining = manager.check_rate_limit(api_key)
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="API key rate limit exceeded",
            headers={"Retry-After": "60", "X-RateLimit-Remaining": "0"}
        )
    
    # Record usage
    manager.record_usage(api_key.key_id)
    
    return api_key
