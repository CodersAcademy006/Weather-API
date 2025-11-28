"""
API Key Management Module

Provides secure API key generation, storage, and validation.
"""

import secrets
import hashlib
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict

from config import settings
from logging_config import get_logger
from storage import get_storage

logger = get_logger(__name__)


@dataclass
class APIKey:
    """API Key model."""
    key_id: str
    user_id: str
    name: str
    key_hash: str  # Only store hash, not the actual key
    key_prefix: str  # First 8 chars for identification
    created_at: str
    expires_at: Optional[str]
    last_used_at: Optional[str]
    rate_limit: int
    total_requests: int
    is_active: bool
    
    @classmethod
    def create(
        cls,
        user_id: str,
        name: str,
        rate_limit: int = None,
        expires_in_days: int = None
    ) -> tuple["APIKey", str]:
        """
        Create a new API key.
        
        Returns:
            Tuple of (APIKey object, raw_key)
        """
        # Generate secure random key
        raw_key = f"iw_live_{secrets.token_hex(24)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:12]
        
        now = datetime.now(timezone.utc)
        expires_at = None
        if expires_in_days:
            expires_at = (now + timedelta(days=expires_in_days)).isoformat()
        
        key = cls(
            key_id=f"key_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            created_at=now.isoformat(),
            expires_at=expires_at,
            last_used_at=None,
            rate_limit=rate_limit or settings.API_KEY_RATE_LIMIT_DEFAULT,
            total_requests=0,
            is_active=True
        )
        
        return key, raw_key
    
    def is_expired(self) -> bool:
        """Check if the key has expired."""
        if not self.expires_at:
            return False
        expires = datetime.fromisoformat(self.expires_at)
        return datetime.now(timezone.utc) > expires
    
    def is_valid(self) -> bool:
        """Check if the key is valid (active and not expired)."""
        return self.is_active and not self.is_expired()


class APIKeyManager:
    """
    Manager for API key operations.
    
    Features:
    - Secure key generation and hashing
    - Key validation
    - Rate limit tracking per key
    - Key revocation
    """
    
    # CSV configuration
    FILE_CONFIG = {
        "filename": "api_keys.csv",
        "headers": [
            "key_id", "user_id", "name", "key_hash", "key_prefix",
            "created_at", "expires_at", "last_used_at", "rate_limit",
            "total_requests", "is_active"
        ]
    }
    
    def __init__(self):
        """Initialize the API key manager."""
        self._init_storage()
        self._rate_limits: Dict[str, List[float]] = {}  # key_id -> list of timestamps
        logger.info("API key manager initialized")
    
    def _init_storage(self) -> None:
        """Initialize the API keys CSV file."""
        import os
        import csv
        from pathlib import Path
        
        data_dir = settings.DATA_DIR
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        
        filepath = os.path.join(data_dir, self.FILE_CONFIG["filename"])
        if not os.path.exists(filepath):
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.FILE_CONFIG["headers"])
            logger.info("Created api_keys.csv")
    
    def _get_filepath(self) -> str:
        """Get the CSV file path."""
        import os
        return os.path.join(settings.DATA_DIR, self.FILE_CONFIG["filename"])
    
    def _read_all(self) -> List[Dict[str, Any]]:
        """Read all API keys from storage."""
        import csv
        with open(self._get_filepath(), "r", newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    
    def _write_all(self, rows: List[Dict[str, Any]]) -> None:
        """Write all API keys to storage."""
        import csv
        with open(self._get_filepath(), "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.FILE_CONFIG["headers"])
            writer.writeheader()
            writer.writerows(rows)
    
    def _append_row(self, row: Dict[str, Any]) -> None:
        """Append a single row to storage."""
        import csv
        with open(self._get_filepath(), "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.FILE_CONFIG["headers"])
            writer.writerow(row)
    
    def create_key(
        self,
        user_id: str,
        name: str,
        rate_limit: int = None,
        expires_in_days: int = None
    ) -> tuple[APIKey, str]:
        """
        Create a new API key for a user.
        
        Args:
            user_id: User ID
            name: Key name/description
            rate_limit: Custom rate limit
            expires_in_days: Key expiration
            
        Returns:
            Tuple of (APIKey object, raw_key)
        """
        api_key, raw_key = APIKey.create(user_id, name, rate_limit, expires_in_days)
        self._append_row(asdict(api_key))
        logger.info(f"Created API key {api_key.key_id} for user {user_id}")
        return api_key, raw_key
    
    def validate_key(self, raw_key: str) -> Optional[APIKey]:
        """
        Validate an API key.
        
        Args:
            raw_key: The raw API key string
            
        Returns:
            APIKey object if valid, None otherwise
        """
        if not raw_key:
            return None
        
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        rows = self._read_all()
        for row in rows:
            if row["key_hash"] == key_hash:
                row["rate_limit"] = int(row.get("rate_limit", settings.API_KEY_RATE_LIMIT_DEFAULT))
                row["total_requests"] = int(row.get("total_requests", 0))
                row["is_active"] = row.get("is_active", "True") == "True"
                
                api_key = APIKey(**row)
                
                if not api_key.is_valid():
                    logger.warning(f"Invalid or expired API key: {api_key.key_prefix}")
                    return None
                
                return api_key
        
        return None
    
    def record_usage(self, key_id: str) -> None:
        """Record API key usage."""
        rows = self._read_all()
        for row in rows:
            if row["key_id"] == key_id:
                row["total_requests"] = str(int(row.get("total_requests", 0)) + 1)
                row["last_used_at"] = datetime.now(timezone.utc).isoformat()
                break
        
        self._write_all(rows)
    
    def check_rate_limit(self, api_key: APIKey) -> tuple[bool, int]:
        """
        Check if API key has exceeded rate limit.
        
        Args:
            api_key: The API key to check
            
        Returns:
            Tuple of (allowed: bool, remaining: int)
        """
        import time
        
        now = time.time()
        window = 60  # 1 minute window
        
        key_id = api_key.key_id
        if key_id not in self._rate_limits:
            self._rate_limits[key_id] = []
        
        # Remove old timestamps
        self._rate_limits[key_id] = [
            ts for ts in self._rate_limits[key_id]
            if now - ts < window
        ]
        
        remaining = api_key.rate_limit - len(self._rate_limits[key_id])
        
        if remaining <= 0:
            return False, 0
        
        self._rate_limits[key_id].append(now)
        return True, remaining - 1
    
    def get_user_keys(self, user_id: str) -> List[APIKey]:
        """Get all API keys for a user."""
        rows = self._read_all()
        keys = []
        
        for row in rows:
            if row["user_id"] == user_id:
                row["rate_limit"] = int(row.get("rate_limit", settings.API_KEY_RATE_LIMIT_DEFAULT))
                row["total_requests"] = int(row.get("total_requests", 0))
                row["is_active"] = row.get("is_active", "True") == "True"
                keys.append(APIKey(**row))
        
        return keys
    
    def revoke_key(self, key_id: str, user_id: str) -> bool:
        """
        Revoke an API key.
        
        Args:
            key_id: Key ID to revoke
            user_id: User ID (for authorization)
            
        Returns:
            True if revoked, False otherwise
        """
        rows = self._read_all()
        found = False
        
        for row in rows:
            if row["key_id"] == key_id and row["user_id"] == user_id:
                row["is_active"] = "False"
                found = True
                break
        
        if found:
            self._write_all(rows)
            logger.info(f"Revoked API key: {key_id}")
        
        return found
    
    def get_key_by_id(self, key_id: str) -> Optional[APIKey]:
        """Get an API key by ID."""
        rows = self._read_all()
        
        for row in rows:
            if row["key_id"] == key_id:
                row["rate_limit"] = int(row.get("rate_limit", settings.API_KEY_RATE_LIMIT_DEFAULT))
                row["total_requests"] = int(row.get("total_requests", 0))
                row["is_active"] = row.get("is_active", "True") == "True"
                return APIKey(**row)
        
        return None


# Global manager instance
_api_key_manager: Optional[APIKeyManager] = None


def get_api_key_manager() -> APIKeyManager:
    """Get the global API key manager instance."""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager
