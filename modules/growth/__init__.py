"""
IntelliWeather - Growth Features Module

Includes:
- Analytics event tracking
- Referral system
- Shareable forecast links
- Social preview image generation
"""

import uuid
import hashlib
import hmac
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel
from config import settings
from logging_config import get_logger

logger = get_logger(__name__)


# ==================== ANALYTICS ====================

class EventType(str, Enum):
    """Analytics event types"""
    PAGE_VIEW = "page_view"
    SEARCH = "search"
    WEATHER_FETCH = "weather_fetch"
    FORECAST_VIEW = "forecast_view"
    ALERT_VIEW = "alert_view"
    SIGNUP = "signup"
    LOGIN = "login"
    SHARE = "share"
    DOWNLOAD = "download"
    API_CALL = "api_call"
    ERROR = "error"


@dataclass
class AnalyticsEvent:
    """Analytics event data"""
    id: str
    event_type: EventType
    timestamp: datetime
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        event_type: EventType,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **properties
    ) -> "AnalyticsEvent":
        return cls(
            id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            session_id=session_id,
            properties=properties
        )
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "session_id": self.session_id,
            "properties": self.properties
        }


class AnalyticsService:
    """In-process analytics event capture"""
    
    def __init__(self, max_events: int = 10000):
        self.events: List[AnalyticsEvent] = []
        self.max_events = max_events
        self.event_counts: Dict[str, int] = {}
    
    def track(
        self,
        event_type: EventType,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **properties
    ) -> AnalyticsEvent:
        """Track an analytics event"""
        event = AnalyticsEvent.create(event_type, user_id, session_id, **properties)
        
        # Store event
        self.events.append(event)
        
        # Update counts
        key = event_type.value
        self.event_counts[key] = self.event_counts.get(key, 0) + 1
        
        # Trim old events if needed
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
        
        logger.debug(f"Analytics event tracked: {event_type.value}")
        return event
    
    def get_recent_events(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 100
    ) -> List[dict]:
        """Get recent events, optionally filtered by type"""
        events = self.events
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        return [e.to_dict() for e in events[-limit:]]
    
    def get_counts(self) -> Dict[str, int]:
        """Get event counts by type"""
        return self.event_counts.copy()
    
    def get_top_searches(self, limit: int = 10) -> List[dict]:
        """Get top search queries"""
        search_events = [e for e in self.events if e.event_type == EventType.SEARCH]
        
        query_counts: Dict[str, int] = {}
        for event in search_events:
            query = event.properties.get("query", "").lower()
            if query:
                query_counts[query] = query_counts.get(query, 0) + 1
        
        sorted_queries = sorted(query_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"query": q, "count": c} for q, c in sorted_queries[:limit]]
    
    def get_stats(self) -> dict:
        """Get analytics statistics"""
        return {
            "total_events": len(self.events),
            "event_counts": self.event_counts,
            "top_searches": self.get_top_searches(5),
            "recent_events_count": len(self.events)
        }


# ==================== REFERRAL SYSTEM ====================

@dataclass
class ReferralCode:
    """Referral code data"""
    code: str
    user_id: str
    created_at: datetime
    uses: int = 0
    max_uses: Optional[int] = None
    expires_at: Optional[datetime] = None
    
    def is_valid(self) -> bool:
        """Check if referral code is still valid"""
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        if self.max_uses and self.uses >= self.max_uses:
            return False
        return True


@dataclass
class Referral:
    """Referral record"""
    id: str
    referrer_id: str
    referred_id: str
    code: str
    created_at: datetime
    status: str = "pending"  # pending, completed, rewarded


class ReferralService:
    """Referral system service"""
    
    def __init__(self):
        self.codes: Dict[str, ReferralCode] = {}
        self.referrals: List[Referral] = []
        self.user_codes: Dict[str, str] = {}  # user_id -> code
    
    def generate_code(
        self,
        user_id: str,
        max_uses: Optional[int] = None,
        expires_days: Optional[int] = 30
    ) -> ReferralCode:
        """Generate a referral code for a user"""
        # Check if user already has a code
        if user_id in self.user_codes:
            return self.codes[self.user_codes[user_id]]
        
        # Generate unique code
        code = self._generate_unique_code(user_id)
        
        expires_at = None
        if expires_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
        
        referral_code = ReferralCode(
            code=code,
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            max_uses=max_uses,
            expires_at=expires_at
        )
        
        self.codes[code] = referral_code
        self.user_codes[user_id] = code
        
        logger.info(f"Referral code generated for user {user_id}: {code}")
        return referral_code
    
    def _generate_unique_code(self, user_id: str) -> str:
        """Generate a unique referral code"""
        data = f"{user_id}:{datetime.now().isoformat()}:{uuid.uuid4()}"
        hash_val = hashlib.sha256(data.encode()).hexdigest()[:8].upper()
        return f"IW-{hash_val}"
    
    def validate_code(self, code: str) -> Optional[ReferralCode]:
        """Validate a referral code"""
        referral_code = self.codes.get(code.upper())
        if referral_code and referral_code.is_valid():
            return referral_code
        return None
    
    def use_code(self, code: str, referred_user_id: str) -> Optional[Referral]:
        """Use a referral code"""
        referral_code = self.validate_code(code)
        if not referral_code:
            return None
        
        # Don't allow self-referral
        if referral_code.user_id == referred_user_id:
            return None
        
        # Create referral record
        referral = Referral(
            id=str(uuid.uuid4()),
            referrer_id=referral_code.user_id,
            referred_id=referred_user_id,
            code=code,
            created_at=datetime.now(timezone.utc),
            status="completed"
        )
        
        # Update code usage
        referral_code.uses += 1
        
        self.referrals.append(referral)
        
        logger.info(f"Referral code {code} used by {referred_user_id}")
        return referral
    
    def get_user_referrals(self, user_id: str) -> List[Referral]:
        """Get referrals made by a user"""
        return [r for r in self.referrals if r.referrer_id == user_id]
    
    def get_user_code(self, user_id: str) -> Optional[ReferralCode]:
        """Get a user's referral code"""
        code = self.user_codes.get(user_id)
        if code:
            return self.codes.get(code)
        return None
    
    def get_stats(self) -> dict:
        """Get referral system statistics"""
        return {
            "total_codes": len(self.codes),
            "total_referrals": len(self.referrals),
            "active_codes": sum(1 for c in self.codes.values() if c.is_valid()),
            "top_referrers": self._get_top_referrers(5)
        }
    
    def _get_top_referrers(self, limit: int) -> List[dict]:
        """Get top referrers by number of referrals"""
        referrer_counts: Dict[str, int] = {}
        for referral in self.referrals:
            referrer_counts[referral.referrer_id] = referrer_counts.get(referral.referrer_id, 0) + 1
        
        sorted_referrers = sorted(referrer_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"user_id": u, "referrals": c} for u, c in sorted_referrers[:limit]]


# ==================== SHAREABLE LINKS ====================

@dataclass
class ShareableLink:
    """Shareable forecast link"""
    token: str
    lat: float
    lon: float
    location_name: str
    created_at: datetime
    expires_at: datetime
    created_by: Optional[str] = None
    view_count: int = 0
    
    def is_valid(self) -> bool:
        """Check if link is still valid"""
        return datetime.now(timezone.utc) < self.expires_at


class ShareableLinkService:
    """Service for creating and managing shareable forecast links"""
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or settings.SECRET_KEY
        self.links: Dict[str, ShareableLink] = {}
    
    def create_link(
        self,
        lat: float,
        lon: float,
        location_name: str,
        expires_hours: int = 168,  # 1 week default
        created_by: Optional[str] = None
    ) -> ShareableLink:
        """Create a shareable forecast link"""
        # Generate signed token
        token = self._generate_token(lat, lon, location_name)
        
        link = ShareableLink(
            token=token,
            lat=lat,
            lon=lon,
            location_name=location_name,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_hours),
            created_by=created_by
        )
        
        self.links[token] = link
        
        logger.info(f"Shareable link created: {token[:8]}...")
        return link
    
    def _generate_token(self, lat: float, lon: float, location_name: str) -> str:
        """Generate a signed token for the link"""
        data = f"{lat}:{lon}:{location_name}:{datetime.now().isoformat()}"
        signature = hmac.new(
            self.secret_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()[:32]  # Use 128 bits (32 hex chars) for security
        
        return f"s_{signature}"
    
    def get_link(self, token: str) -> Optional[ShareableLink]:
        """Get a shareable link by token"""
        link = self.links.get(token)
        if link and link.is_valid():
            link.view_count += 1
            return link
        return None
    
    def get_link_url(self, link: ShareableLink, base_url: str = "") -> str:
        """Get the full URL for a shareable link"""
        return f"{base_url}/s/{link.token}"
    
    def get_user_links(self, user_id: str) -> List[ShareableLink]:
        """Get all links created by a user"""
        return [l for l in self.links.values() if l.created_by == user_id and l.is_valid()]
    
    def cleanup_expired(self) -> int:
        """Remove expired links"""
        expired = [k for k, v in self.links.items() if not v.is_valid()]
        for key in expired:
            del self.links[key]
        return len(expired)


# ==================== SOCIAL PREVIEW ====================

class SocialPreviewData(BaseModel):
    """Data for generating social preview images"""
    location: str
    temperature: float
    condition: str
    icon: str
    high: Optional[float] = None
    low: Optional[float] = None
    
    def to_og_title(self) -> str:
        """Generate Open Graph title"""
        return f"Weather in {self.location} - {self.temperature}°C"
    
    def to_og_description(self) -> str:
        """Generate Open Graph description"""
        desc = f"Current: {self.condition}, {self.temperature}°C"
        if self.high and self.low:
            desc += f" | High: {self.high}°C, Low: {self.low}°C"
        desc += " | IntelliWeather"
        return desc


class SocialPreviewService:
    """Service for generating social preview metadata"""
    
    def generate_meta_tags(self, data: SocialPreviewData, url: str) -> str:
        """Generate Open Graph and Twitter meta tags"""
        tags = f"""
<meta property="og:type" content="website">
<meta property="og:title" content="{data.to_og_title()}">
<meta property="og:description" content="{data.to_og_description()}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{url}/preview.png">
<meta property="og:site_name" content="IntelliWeather">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{data.to_og_title()}">
<meta name="twitter:description" content="{data.to_og_description()}">
<meta name="twitter:image" content="{url}/preview.png">
"""
        return tags.strip()
    
    def generate_preview_html(self, data: SocialPreviewData) -> str:
        """Generate HTML for screenshot-based preview image generation"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            width: 1200px;
            height: 630px;
            font-family: 'Inter', system-ui, sans-serif;
            background: linear-gradient(135deg, #4a1c6e, #7b4397);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .card {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 48px;
            text-align: center;
            width: 80%;
        }}
        .icon {{ font-size: 120px; margin-bottom: 16px; }}
        .temp {{ font-size: 96px; font-weight: 700; margin-bottom: 8px; }}
        .location {{ font-size: 36px; opacity: 0.9; margin-bottom: 16px; }}
        .condition {{ font-size: 24px; opacity: 0.8; }}
        .range {{ font-size: 20px; opacity: 0.7; margin-top: 16px; }}
        .brand {{ position: absolute; bottom: 24px; right: 24px; font-size: 18px; opacity: 0.7; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">{data.icon}</div>
        <div class="temp">{data.temperature}°C</div>
        <div class="location">{data.location}</div>
        <div class="condition">{data.condition}</div>
        {"<div class='range'>H: " + str(data.high) + "°C | L: " + str(data.low) + "°C</div>" if data.high else ""}
    </div>
    <div class="brand">🌤️ IntelliWeather</div>
</body>
</html>
"""


# ==================== GLOBAL SERVICE INSTANCES ====================

_analytics_service: Optional[AnalyticsService] = None
_referral_service: Optional[ReferralService] = None
_shareable_link_service: Optional[ShareableLinkService] = None
_social_preview_service: Optional[SocialPreviewService] = None


def get_analytics_service() -> AnalyticsService:
    """Get analytics service singleton"""
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = AnalyticsService()
    return _analytics_service


def get_referral_service() -> ReferralService:
    """Get referral service singleton"""
    global _referral_service
    if _referral_service is None:
        _referral_service = ReferralService()
    return _referral_service


def get_shareable_link_service() -> ShareableLinkService:
    """Get shareable link service singleton"""
    global _shareable_link_service
    if _shareable_link_service is None:
        _shareable_link_service = ShareableLinkService()
    return _shareable_link_service


def get_social_preview_service() -> SocialPreviewService:
    """Get social preview service singleton"""
    global _social_preview_service
    if _social_preview_service is None:
        _social_preview_service = SocialPreviewService()
    return _social_preview_service
