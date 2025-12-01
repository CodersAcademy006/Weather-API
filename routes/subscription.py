"""
Subscription and Billing Routes

Endpoints for managing subscriptions, viewing pricing, and billing.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from typing import Dict, Any

from modules.subscription_tiers import (
    get_all_tiers,
    get_tier_limits,
    SubscriptionTier,
    get_tier_from_string
)
from middleware.api_key_auth import get_rate_limiter
from session_middleware import require_auth, get_session, SessionData
from storage import get_storage
from logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v3/subscription", tags=["Subscription & Billing"])


@router.get("/tiers")
async def get_pricing_tiers():
    """
    Get all available subscription tiers and pricing.
    
    Returns pricing, features, and limits for each tier.
    """
    tiers = get_all_tiers()
    
    return {
        "status": "success",
        "tiers": tiers,
        "note": "Prices in USD per month"
    }


@router.get("/my-tier")
async def get_my_subscription_tier(session: SessionData = Depends(get_session)):
    """
    Get current user's subscription tier and usage.
    
    Requires authentication.
    """
    if not session.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    storage = get_storage()
    user = storage.get_user_by_id(session.user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    tier = SubscriptionTier(user.get("subscription_tier", "free"))
    tier_limits = get_tier_limits(tier)
    
    # Get API keys for this user
    api_keys = storage.get_api_keys_by_user(session.user_id)
    
    # Calculate total usage across all keys (simplified for now)
    total_usage = {
        "hourly": 0,
        "daily": 0,
        "monthly": 0
    }
    
    return {
        "status": "success",
        "user_id": session.user_id,
        "current_tier": {
            "name": tier.value,
            "display_name": tier_limits.display_name,
            "price_monthly": tier_limits.price_monthly,
            "features": tier_limits.features
        },
        "limits": {
            "requests_per_hour": tier_limits.requests_per_hour,
            "requests_per_day": tier_limits.requests_per_day,
            "requests_per_month": tier_limits.requests_per_month,
            "max_api_keys": tier_limits.max_api_keys
        },
        "usage": {
            "hourly": {
                "used": total_usage["hourly"],
                "limit": tier_limits.requests_per_hour,
                "remaining": max(0, tier_limits.requests_per_hour - total_usage["hourly"]),
                "percentage": round((total_usage["hourly"] / tier_limits.requests_per_hour) * 100, 2)
            },
            "daily": {
                "used": total_usage["daily"],
                "limit": tier_limits.requests_per_day,
                "remaining": max(0, tier_limits.requests_per_day - total_usage["daily"]),
                "percentage": round((total_usage["daily"] / tier_limits.requests_per_day) * 100, 2)
            },
            "monthly": {
                "used": total_usage["monthly"],
                "limit": tier_limits.requests_per_month,
                "remaining": max(0, tier_limits.requests_per_month - total_usage["monthly"]),
                "percentage": round((total_usage["monthly"] / tier_limits.requests_per_month) * 100, 2)
            }
        },
        "api_keys": {
            "active": len([k for k in api_keys if k.get("is_active")]),
            "total": len(api_keys),
            "limit": tier_limits.max_api_keys
        }
    }


@router.post("/upgrade")
async def upgrade_subscription(
    tier: str,
    session: SessionData = Depends(require_auth)
):
    """
    Upgrade user's subscription tier.
    
    Note: In production, this would integrate with Stripe or another payment processor.
    For now, this is a placeholder that updates the tier directly.
    """
    try:
        new_tier = get_tier_from_string(tier)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier: {tier}. Must be one of: free, pro, business, enterprise"
        )
    
    storage = get_storage()
    user = storage.get_user_by_id(session.user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    current_tier = SubscriptionTier(user.get("subscription_tier", "free"))
    
    if new_tier == current_tier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Already subscribed to {new_tier.value} tier"
        )
    
    # Update user's subscription tier
    storage.update_user_subscription_tier(session.user_id, new_tier.value)
    
    new_tier_limits = get_tier_limits(new_tier)
    
    logger.info(f"User {session.user_id} upgraded from {current_tier.value} to {new_tier.value}")
    
    return {
        "status": "success",
        "message": f"Successfully upgraded to {new_tier_limits.display_name} tier",
        "previous_tier": current_tier.value,
        "new_tier": new_tier.value,
        "new_limits": {
            "requests_per_hour": new_tier_limits.requests_per_hour,
            "requests_per_day": new_tier_limits.requests_per_day,
            "requests_per_month": new_tier_limits.requests_per_month,
            "max_api_keys": new_tier_limits.max_api_keys
        },
        "note": "In production, this would process payment via Stripe"
    }


@router.get("/usage-history")
async def get_usage_history(
    days: int = 7,
    session: SessionData = Depends(require_auth)
):
    """
    Get historical usage data for the user's API keys.
    
    Args:
        days: Number of days of history (default: 7, max: 90)
    """
    if days < 1 or days > 90:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Days must be between 1 and 90"
        )
    
    storage = get_storage()
    user = storage.get_user_by_id(session.user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get API keys
    api_keys = storage.get_api_keys_by_user(session.user_id)
    
    # In a production system, this would query a time-series database
    # For now, return current stats
    tier = SubscriptionTier(user.get("subscription_tier", "free"))
    rate_limiter = get_api_key_rate_limiter()
    
    # Get API keys
    api_keys = storage.get_api_keys_by_user(session.user_id)
    
    # In a production system, this would query usage tracking data
    # For now, return simplified stats
    tier = SubscriptionTier(user.get("subscription_tier", "free"))
    
    keys_usage = []
    for key in api_keys:
        if key.get("is_active"):
            keys_usage.append({
                "key_id": key["key_id"],
                "key_name": key["name"],
                "key_prefix": key["key_prefix"],
                "usage": {
                    "hourly": {"used": 0, "limit": 60},
                    "daily": {"used": 0, "limit": 1000},
                    "monthly": {"used": 0, "limit": 10000}
                }
            })
    
    return {
        "status": "success",
        "period": "last_30_days",
        "keys": keys_usage
    }
