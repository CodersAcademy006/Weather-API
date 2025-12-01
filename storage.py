"""
CSV/Excel-backed Data Storage Layer

This module provides a simple database using CSV files with:
- User storage (user_id, username, email, hashed_password, created_at)
- Session storage (session_id, user_id, created_at, last_active_at, expires_at)
- User search history
- Cached weather results for popular locations
- Thread-safe file operations
- Auto-creation of data directory and CSV files with headers
"""

import csv
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict, field
from pathlib import Path
from config import settings
from logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class User:
    """User model."""
    user_id: str
    username: str
    email: str
    hashed_password: str
    created_at: str
    is_active: bool = True
    subscription_tier: str = "free"  # free, pro, business, enterprise
    
    @classmethod
    def create(cls, username: str, email: str, hashed_password: str) -> "User":
        """Create a new user with auto-generated ID and timestamp."""
        return cls(
            user_id=str(uuid.uuid4()),
            username=username,
            email=email,
            hashed_password=hashed_password,
            created_at=datetime.now(timezone.utc).isoformat(),
            subscription_tier="free"
        )


@dataclass
class Session:
    """Session model."""
    session_id: str
    user_id: str
    created_at: str
    last_active_at: str
    expires_at: str
    is_valid: bool = True
    
    @classmethod
    def create(cls, user_id: str, ttl_seconds: int = None) -> "Session":
        """Create a new session with auto-generated ID and timestamps."""
        ttl = ttl_seconds or settings.SESSION_TIMEOUT_SECONDS
        now = datetime.now(timezone.utc)
        expires = now.timestamp() + ttl
        
        return cls(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            created_at=now.isoformat(),
            last_active_at=now.isoformat(),
            expires_at=datetime.fromtimestamp(expires, timezone.utc).isoformat()
        )
    
    def is_expired(self) -> bool:
        """Check if the session has expired."""
        expires = datetime.fromisoformat(self.expires_at)
        return datetime.now(timezone.utc) > expires


@dataclass
class SearchHistory:
    """User search history model."""
    id: str
    user_id: str
    query: str
    lat: float
    lon: float
    searched_at: str
    
    @classmethod
    def create(cls, user_id: str, query: str, lat: float, lon: float) -> "SearchHistory":
        """Create a new search history entry."""
        return cls(
            id=str(uuid.uuid4()),
            user_id=user_id,
            query=query,
            lat=lat,
            lon=lon,
            searched_at=datetime.now(timezone.utc).isoformat()
        )


@dataclass
class CachedWeather:
    """Cached weather data model."""
    cache_key: str
    lat: float
    lon: float
    location_name: str
    data_type: str  # current, hourly, daily, aqi
    data: str  # JSON string
    created_at: str
    expires_at: str
    hit_count: int = 0
    
    @classmethod
    def create(
        cls,
        lat: float,
        lon: float,
        location_name: str,
        data_type: str,
        data: str,
        ttl_seconds: int = None
    ) -> "CachedWeather":
        """Create a new cached weather entry."""
        ttl = ttl_seconds or settings.CACHE_TTL_SECONDS
        now = datetime.now(timezone.utc)
        expires = now.timestamp() + ttl
        
        return cls(
            cache_key=f"{data_type}:{round(lat, 2)}:{round(lon, 2)}",
            lat=lat,
            lon=lon,
            location_name=location_name,
            data_type=data_type,
            data=data,
            created_at=now.isoformat(),
            expires_at=datetime.fromtimestamp(expires, timezone.utc).isoformat()
        )


class CSVStorage:
    """
    Thread-safe CSV-based storage system.
    
    Provides CRUD operations for users, sessions, search history,
    and cached weather data.
    """
    
    # CSV file configurations
    FILES = {
        "users": {
            "filename": "users.csv",
            "headers": ["user_id", "username", "email", "hashed_password", "created_at", "is_active", "subscription_tier"]
        },
        "sessions": {
            "filename": "sessions.csv",
            "headers": ["session_id", "user_id", "created_at", "last_active_at", "expires_at", "is_valid"]
        },
        "search_history": {
            "filename": "search_history.csv",
            "headers": ["id", "user_id", "query", "lat", "lon", "searched_at"]
        },
        "cached_weather": {
            "filename": "cached_weather.csv",
            "headers": ["cache_key", "lat", "lon", "location_name", "data_type", "data", "created_at", "expires_at", "hit_count"]
        }
    }
    
    def __init__(self, data_dir: str = None):
        """
        Initialize the storage system.
        
        Args:
            data_dir: Directory for CSV files (uses settings if not specified)
        """
        self._data_dir = data_dir or settings.DATA_DIR
        self._locks: Dict[str, threading.RLock] = {
            name: threading.RLock() for name in self.FILES
        }
        self._init_storage()
        logger.info(f"CSV storage initialized at {self._data_dir}")
    
    def _init_storage(self) -> None:
        """Initialize storage directory and CSV files."""
        # Create data directory
        Path(self._data_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize each CSV file with headers if it doesn't exist
        for name, config in self.FILES.items():
            filepath = self._get_filepath(name)
            if not os.path.exists(filepath):
                with open(filepath, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(config["headers"])
                logger.info(f"Created {config['filename']} with headers")
    
    def _get_filepath(self, file_type: str) -> str:
        """Get the full path for a CSV file."""
        return os.path.join(self._data_dir, self.FILES[file_type]["filename"])
    
    def _read_all(self, file_type: str) -> List[Dict[str, Any]]:
        """Read all rows from a CSV file."""
        filepath = self._get_filepath(file_type)
        headers = self.FILES[file_type]["headers"]
        
        with self._locks[file_type]:
            with open(filepath, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return list(reader)
    
    def _write_all(self, file_type: str, rows: List[Dict[str, Any]]) -> None:
        """Write all rows to a CSV file."""
        filepath = self._get_filepath(file_type)
        headers = self.FILES[file_type]["headers"]
        
        with self._locks[file_type]:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)
    
    def _append_row(self, file_type: str, row: Dict[str, Any]) -> None:
        """Append a single row to a CSV file."""
        filepath = self._get_filepath(file_type)
        headers = self.FILES[file_type]["headers"]
        
        with self._locks[file_type]:
            with open(filepath, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writerow(row)
    
    # ==================== USER OPERATIONS ====================
    
    def create_user(self, user: User) -> User:
        """Create a new user."""
        # Check for existing user
        existing = self.get_user_by_email(user.email)
        if existing:
            raise ValueError(f"User with email {user.email} already exists")
        
        existing = self.get_user_by_username(user.username)
        if existing:
            raise ValueError(f"User with username {user.username} already exists")
        
        self._append_row("users", asdict(user))
        logger.info(f"Created user: {user.username}")
        return user
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        rows = self._read_all("users")
        for row in rows:
            if row["user_id"] == user_id:
                row["is_active"] = row.get("is_active", "True") == "True"
                return User(**row)
        return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        rows = self._read_all("users")
        for row in rows:
            if row["email"].lower() == email.lower():
                row["is_active"] = row.get("is_active", "True") == "True"
                return User(**row)
        return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get a user by username."""
        rows = self._read_all("users")
        for row in rows:
            if row["username"].lower() == username.lower():
                row["is_active"] = row.get("is_active", "True") == "True"
                return User(**row)
        return None
    
    def update_user(self, user: User) -> User:
        """Update an existing user."""
        rows = self._read_all("users")
        updated = False
        
        for i, row in enumerate(rows):
            if row["user_id"] == user.user_id:
                rows[i] = asdict(user)
                updated = True
                break
        
        if updated:
            self._write_all("users", rows)
            logger.info(f"Updated user: {user.username}")
        
        return user
    
    def get_all_users(self) -> List[User]:
        """Get all users."""
        rows = self._read_all("users")
        return [User(**{**row, "is_active": row.get("is_active", "True") == "True"}) for row in rows]
    
    # ==================== SESSION OPERATIONS ====================
    
    def create_session(self, session: Session) -> Session:
        """Create a new session."""
        self._append_row("sessions", asdict(session))
        logger.info(f"Created session for user: {session.user_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        rows = self._read_all("sessions")
        for row in rows:
            if row["session_id"] == session_id:
                row["is_valid"] = row.get("is_valid", "True") == "True"
                return Session(**row)
        return None
    
    def update_session(self, session: Session) -> Session:
        """Update a session (e.g., last_active_at)."""
        rows = self._read_all("sessions")
        updated = False
        
        for i, row in enumerate(rows):
            if row["session_id"] == session.session_id:
                rows[i] = asdict(session)
                updated = True
                break
        
        if updated:
            self._write_all("sessions", rows)
        
        return session
    
    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session."""
        session = self.get_session(session_id)
        if session:
            session.is_valid = False
            self.update_session(session)
            logger.info(f"Invalidated session: {session_id}")
            return True
        return False
    
    def get_user_sessions(self, user_id: str, valid_only: bool = True) -> List[Session]:
        """Get all sessions for a user."""
        rows = self._read_all("sessions")
        sessions = []
        
        for row in rows:
            if row["user_id"] == user_id:
                row["is_valid"] = row.get("is_valid", "True") == "True"
                session = Session(**row)
                if not valid_only or (session.is_valid and not session.is_expired()):
                    sessions.append(session)
        
        return sessions
    
    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions."""
        rows = self._read_all("sessions")
        valid_rows = []
        removed = 0
        
        for row in rows:
            row["is_valid"] = row.get("is_valid", "True") == "True"
            session = Session(**row)
            if session.is_valid and not session.is_expired():
                valid_rows.append(row)
            else:
                removed += 1
        
        if removed > 0:
            self._write_all("sessions", valid_rows)
            logger.info(f"Cleaned up {removed} expired sessions")
        
        return removed
    
    def count_active_sessions(self) -> int:
        """Count active (valid and not expired) sessions."""
        rows = self._read_all("sessions")
        count = 0
        
        for row in rows:
            row["is_valid"] = row.get("is_valid", "True") == "True"
            session = Session(**row)
            if session.is_valid and not session.is_expired():
                count += 1
        
        return count
    
    # ==================== SEARCH HISTORY OPERATIONS ====================
    
    def add_search_history(self, entry: SearchHistory) -> SearchHistory:
        """Add a search history entry."""
        self._append_row("search_history", asdict(entry))
        return entry
    
    def get_user_search_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[SearchHistory]:
        """Get search history for a user."""
        rows = self._read_all("search_history")
        history = [
            SearchHistory(**{**row, "lat": float(row["lat"]), "lon": float(row["lon"])})
            for row in rows
            if row["user_id"] == user_id
        ]
        # Sort by most recent and limit
        history.sort(key=lambda x: x.searched_at, reverse=True)
        return history[:limit]
    
    # ==================== CACHED WEATHER OPERATIONS ====================
    
    def save_cached_weather(self, entry: CachedWeather) -> CachedWeather:
        """Save or update cached weather data."""
        rows = self._read_all("cached_weather")
        
        # Check if entry exists
        for i, row in enumerate(rows):
            if row["cache_key"] == entry.cache_key:
                rows[i] = asdict(entry)
                self._write_all("cached_weather", rows)
                return entry
        
        # New entry
        self._append_row("cached_weather", asdict(entry))
        return entry
    
    def get_cached_weather(self, cache_key: str) -> Optional[CachedWeather]:
        """Get cached weather data."""
        rows = self._read_all("cached_weather")
        
        for row in rows:
            if row["cache_key"] == cache_key:
                # Check expiration
                expires = datetime.fromisoformat(row["expires_at"])
                if datetime.now(timezone.utc) > expires:
                    return None
                
                return CachedWeather(
                    **{
                        **row,
                        "lat": float(row["lat"]),
                        "lon": float(row["lon"]),
                        "hit_count": int(row.get("hit_count", 0))
                    }
                )
        
        return None
    
    def increment_weather_cache_hits(self, cache_key: str) -> None:
        """Increment hit count for cached weather."""
        rows = self._read_all("cached_weather")
        
        for i, row in enumerate(rows):
            if row["cache_key"] == cache_key:
                rows[i]["hit_count"] = str(int(row.get("hit_count", 0)) + 1)
                self._write_all("cached_weather", rows)
                break
    
    def cleanup_expired_weather_cache(self) -> int:
        """Remove expired weather cache entries."""
        rows = self._read_all("cached_weather")
        valid_rows = []
        removed = 0
        now = datetime.now(timezone.utc)
        
        for row in rows:
            expires = datetime.fromisoformat(row["expires_at"])
            if now <= expires:
                valid_rows.append(row)
            else:
                removed += 1
        
        if removed > 0:
            self._write_all("cached_weather", valid_rows)
            logger.info(f"Cleaned up {removed} expired weather cache entries")
        
        return removed
    
    # ==================== UTILITY METHODS ====================
    
    def is_writable(self) -> bool:
        """Check if storage is writable."""
        try:
            test_file = os.path.join(self._data_dir, ".write_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            return True
        except Exception:
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        return {
            "users_count": len(self._read_all("users")),
            "sessions_count": self.count_active_sessions(),
            "search_history_count": len(self._read_all("search_history")),
            "cached_weather_count": len(self._read_all("cached_weather")),
            "data_directory": self._data_dir,
            "is_writable": self.is_writable()
        }
    
    # ==================== SUBSCRIPTION TIER OPERATIONS ====================
    
    def update_user_subscription_tier(self, user_id: str, tier: str) -> bool:
        """
        Update a user's subscription tier.
        
        Args:
            user_id: User ID
            tier: New tier (free, pro, business, enterprise)
            
        Returns:
            True if updated, False if user not found
        """
        rows = self._read_all("users")
        updated = False
        
        for i, row in enumerate(rows):
            if row["user_id"] == user_id:
                rows[i]["subscription_tier"] = tier
                updated = True
                logger.info(f"Updated user {user_id} subscription tier to {tier}")
                break
        
        if updated:
            self._write_all("users", rows)
        
        return updated
    
    def update_api_key_last_used(self, key_id: str) -> bool:
        """Update the last_used_at timestamp for an API key."""
        # This would be implemented if we stored API keys in CSV
        # For now, it's handled in modules/api_keys.py
        pass


# Global storage instance
_storage: Optional[CSVStorage] = None


def get_storage() -> CSVStorage:
    """
    Get the global storage instance.
    
    Returns:
        The global CSVStorage instance
    """
    global _storage
    if _storage is None:
        _storage = CSVStorage()
    return _storage


def init_storage(data_dir: str = None) -> CSVStorage:
    """
    Initialize (or reinitialize) the global storage.
    
    Args:
        data_dir: Optional custom data directory
        
    Returns:
        The new CSVStorage instance
    """
    global _storage
    _storage = CSVStorage(data_dir)
    return _storage
