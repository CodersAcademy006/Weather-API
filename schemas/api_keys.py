"""
API Keys Schemas

Provides Pydantic models for API key management.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class APIKeyCreate(BaseModel):
    """Request model for creating a new API key."""
    name: str = Field(..., min_length=1, max_length=100, description="Key name/description", example="My App Key")
    rate_limit: Optional[int] = Field(None, ge=1, le=10000, description="Custom rate limit (requests/min)")
    expires_in_days: Optional[int] = Field(None, ge=1, le=365, description="Key expiration in days")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Production API Key",
                "rate_limit": 100,
                "expires_in_days": 90
            }
        }


class APIKeyResponse(BaseModel):
    """Response model for a single API key."""
    key_id: str = Field(..., description="Unique key identifier")
    name: str = Field(..., description="Key name/description")
    key_prefix: str = Field(..., description="First 8 characters of the key", example="iw_live_")
    created_at: str = Field(..., description="When the key was created")
    expires_at: Optional[str] = Field(None, description="When the key expires")
    last_used_at: Optional[str] = Field(None, description="When the key was last used")
    rate_limit: int = Field(..., description="Rate limit (requests/min)")
    total_requests: int = Field(0, description="Total requests made with this key")
    is_active: bool = Field(True, description="Whether the key is active")

    class Config:
        json_schema_extra = {
            "example": {
                "key_id": "key_abc123",
                "name": "Production API Key",
                "key_prefix": "iw_live_",
                "created_at": "2024-01-15T12:00:00Z",
                "expires_at": "2024-04-15T12:00:00Z",
                "last_used_at": "2024-01-15T14:30:00Z",
                "rate_limit": 100,
                "total_requests": 1523,
                "is_active": True
            }
        }


class APIKeyCreated(BaseModel):
    """Response when a new API key is created (includes full key)."""
    key_id: str = Field(..., description="Unique key identifier")
    name: str = Field(..., description="Key name/description")
    api_key: str = Field(..., description="The full API key (only shown once!)")
    created_at: str = Field(..., description="When the key was created")
    expires_at: Optional[str] = Field(None, description="When the key expires")
    rate_limit: int = Field(..., description="Rate limit (requests/min)")
    warning: str = Field(
        "Store this key securely. It will not be shown again.",
        description="Important warning"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "key_id": "key_abc123",
                "name": "Production API Key",
                "api_key": "iw_live_sk_1234567890abcdef",
                "created_at": "2024-01-15T12:00:00Z",
                "expires_at": "2024-04-15T12:00:00Z",
                "rate_limit": 100,
                "warning": "Store this key securely. It will not be shown again."
            }
        }


class APIKeyList(BaseModel):
    """Response model for listing API keys."""
    keys: List[APIKeyResponse] = Field(..., description="List of API keys")
    count: int = Field(..., description="Total number of keys")

    class Config:
        json_schema_extra = {
            "example": {
                "keys": [
                    {
                        "key_id": "key_abc123",
                        "name": "Production API Key",
                        "key_prefix": "iw_live_",
                        "created_at": "2024-01-15T12:00:00Z",
                        "rate_limit": 100,
                        "is_active": True
                    }
                ],
                "count": 1
            }
        }


class APIKeyRevoke(BaseModel):
    """Request to revoke an API key."""
    key_id: str = Field(..., description="Key ID to revoke")

    class Config:
        json_schema_extra = {
            "example": {
                "key_id": "key_abc123"
            }
        }
