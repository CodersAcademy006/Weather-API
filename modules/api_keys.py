"""
API Key Management Module - Complete LEVEL 3 Implementation

Provides secure API key generation, storage, validation, and usage tracking.
"""

import secrets
import hashlib
import uuid
import csv
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path

from config import settings
from logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class APIKey:
    """API Key model with tier-based access."""
    key_id: str
    user_id: str
    name: str
    key_hash: str
    key_prefix: str
    created_at: str
    expires_at: Optional[str]
    last_used_at: Optional[str]
    is_active: bool
    subscription_tier: str  # free, pro, business, enterprise
    
    @classmethod
    def create(
        cls,
        user_id: str,
        name: str,
        subscription_tier: str = "free",
        expires_in_days: int = None
    ) -> tuple["APIKey", str]:
        """Create a new API key. Returns (APIKey, raw_key)."""
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
            is_active=True,
            subscription_tier=subscription_tier
        )
        
        return key, raw_key
    
    def is_expired(self) -> bool:
        """Check if key has expired."""
        if not self.expires_at:
            return False
        expires = datetime.fromisoformat(self.expires_at)
        return datetime.now(timezone.utc) > expires
    
    def is_valid(self) -> bool:
        """Check if key is valid (active and not expired)."""
        return self.is_active and not self.is_expired()


class APIKeyManager:
    """Manager for API key operations with CSV storage."""
    
    def __init__(self, data_dir: str = "data"):
        """Initialize API key manager."""
        self.data_dir = Path(data_dir)
        self.api_keys_file = self.data_dir / "api_keys.csv"
        self.usage_file = self.data_dir / "usage_tracking.csv"
        self._ensure_files()
        
    def _ensure_files(self):
        """Ensure CSV files exist with headers."""
        self.data_dir.mkdir(exist_ok=True)
        
        if not self.api_keys_file.exists():
            with open(self.api_keys_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'key_id', 'user_id', 'name', 'key_hash', 'key_prefix',
                    'created_at', 'expires_at', 'last_used_at', 'is_active', 'subscription_tier'
                ])
        
        if not self.usage_file.exists():
            with open(self.usage_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'usage_id', 'key_id', 'user_id', 'endpoint', 'method',
                    'timestamp', 'status_code', 'latency_ms', 'success'
                ])
    
    def create_key(
        self,
        user_id: str,
        name: str,
        subscription_tier: str = "free",
        expires_in_days: int = None
    ) -> tuple[APIKey, str]:
        """Create and store new API key."""
        api_key, raw_key = APIKey.create(user_id, name, subscription_tier, expires_in_days)
        
        with open(self.api_keys_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'key_id', 'user_id', 'name', 'key_hash', 'key_prefix',
                'created_at', 'expires_at', 'last_used_at', 'is_active', 'subscription_tier'
            ])
            writer.writerow({
                'key_id': api_key.key_id,
                'user_id': api_key.user_id,
                'name': api_key.name,
                'key_hash': api_key.key_hash,
                'key_prefix': api_key.key_prefix,
                'created_at': api_key.created_at,
                'expires_at': api_key.expires_at or '',
                'last_used_at': api_key.last_used_at or '',
                'is_active': str(api_key.is_active),
                'subscription_tier': api_key.subscription_tier
            })
        
        logger.info(f"Created API key {api_key.key_id} for user {user_id}")
        return api_key, raw_key
    
    def validate_key(self, raw_key: str) -> Optional[APIKey]:
        """Validate API key and return APIKey object if valid."""
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        with open(self.api_keys_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['key_hash'] == key_hash:
                    api_key = APIKey(
                        key_id=row['key_id'],
                        user_id=row['user_id'],
                        name=row['name'],
                        key_hash=row['key_hash'],
                        key_prefix=row['key_prefix'],
                        created_at=row['created_at'],
                        expires_at=row['expires_at'] or None,
                        last_used_at=row['last_used_at'] or None,
                        is_active=row['is_active'].lower() == 'true',
                        subscription_tier=row['subscription_tier']
                    )
                    
                    if api_key.is_valid():
                        self._update_last_used(api_key.key_id)
                        return api_key
        
        return None
    
    def get_user_keys(self, user_id: str) -> List[APIKey]:
        """Get all API keys for a user."""
        keys = []
        
        with open(self.api_keys_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['user_id'] == user_id:
                    keys.append(APIKey(
                        key_id=row['key_id'],
                        user_id=row['user_id'],
                        name=row['name'],
                        key_hash=row['key_hash'],
                        key_prefix=row['key_prefix'],
                        created_at=row['created_at'],
                        expires_at=row['expires_at'] or None,
                        last_used_at=row['last_used_at'] or None,
                        is_active=row['is_active'].lower() == 'true',
                        subscription_tier=row['subscription_tier']
                    ))
        
        return keys
    
    def revoke_key(self, key_id: str, user_id: str) -> bool:
        """Revoke an API key."""
        rows = []
        found = False
        
        with open(self.api_keys_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['key_id'] == key_id and row['user_id'] == user_id:
                    row['is_active'] = 'False'
                    found = True
                rows.append(row)
        
        if found:
            with open(self.api_keys_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'key_id', 'user_id', 'name', 'key_hash', 'key_prefix',
                    'created_at', 'expires_at', 'last_used_at', 'is_active', 'subscription_tier'
                ])
                writer.writeheader()
                writer.writerows(rows)
            logger.info(f"Revoked API key {key_id}")
        
        return found
    
    def _update_last_used(self, key_id: str):
        """Update last_used_at timestamp."""
        rows = []
        now = datetime.now(timezone.utc).isoformat()
        
        with open(self.api_keys_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['key_id'] == key_id:
                    row['last_used_at'] = now
                rows.append(row)
        
        with open(self.api_keys_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'key_id', 'user_id', 'name', 'key_hash', 'key_prefix',
                'created_at', 'expires_at', 'last_used_at', 'is_active', 'subscription_tier'
            ])
            writer.writeheader()
            writer.writerows(rows)
    
    def track_usage(
        self,
        key_id: str,
        user_id: str,
        endpoint: str,
        method: str,
        status_code: int,
        latency_ms: float,
        success: bool
    ):
        """Track API usage for metering and analytics."""
        usage_id = f"usage_{uuid.uuid4().hex[:16]}"
        timestamp = datetime.now(timezone.utc).isoformat()
        
        with open(self.usage_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'usage_id', 'key_id', 'user_id', 'endpoint', 'method',
                'timestamp', 'status_code', 'latency_ms', 'success'
            ])
            writer.writerow({
                'usage_id': usage_id,
                'key_id': key_id,
                'user_id': user_id,
                'endpoint': endpoint,
                'method': method,
                'timestamp': timestamp,
                'status_code': status_code,
                'latency_ms': f"{latency_ms:.2f}",
                'success': str(success)
            })
    
    def get_usage_stats(self, key_id: str, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics for an API key."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        total = 0
        successful = 0
        failed = 0
        latencies = []
        
        with open(self.usage_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['key_id'] == key_id:
                    timestamp = datetime.fromisoformat(row['timestamp'])
                    if timestamp >= cutoff:
                        total += 1
                        if row['success'].lower() == 'true':
                            successful += 1
                        else:
                            failed += 1
                        latencies.append(float(row['latency_ms']))
        
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        
        return {
            'total_requests': total,
            'successful': successful,
            'failed': failed,
            'success_rate': (successful / total * 100) if total > 0 else 0,
            'avg_latency_ms': round(avg_latency, 2),
            'period_days': days
        }


# Global manager instance
_api_key_manager = None


def get_api_key_manager() -> APIKeyManager:
    """Get global API key manager instance."""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager
