"""
IntelliWeather - Growth Routes

Endpoints for analytics, referrals, and shareable links.
"""

from fastapi import APIRouter, Request, Response, HTTPException, Depends
from typing import Optional, List
from pydantic import BaseModel

from modules.growth import (
    get_analytics_service,
    get_referral_service,
    get_shareable_link_service,
    get_social_preview_service,
    EventType,
    SocialPreviewData
)
from session_middleware import require_auth
from config import settings
from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/growth", tags=["Growth"])


# ==================== SCHEMAS ====================

class TrackEventRequest(BaseModel):
    """Track event request body"""
    event_type: str
    properties: dict = {}


class CreateShareLinkRequest(BaseModel):
    """Create shareable link request"""
    lat: float
    lon: float
    location_name: str
    expires_hours: int = 168  # 1 week


class ReferralCodeResponse(BaseModel):
    """Referral code response"""
    code: str
    uses: int
    max_uses: Optional[int]
    expires_at: Optional[str]
    referral_url: str


class ShareableLinkResponse(BaseModel):
    """Shareable link response"""
    token: str
    url: str
    location_name: str
    expires_at: str
    view_count: int


# ==================== ANALYTICS ENDPOINTS ====================

@router.post("/analytics/track")
async def track_event(
    request: Request,
    body: TrackEventRequest
):
    """
    Track an analytics event.
    
    Used by frontend to track user interactions.
    """
    if not settings.FEATURE_ANALYTICS:
        raise HTTPException(status_code=503, detail="Analytics is disabled")
    
    try:
        event_type = EventType(body.event_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid event type: {body.event_type}")
    
    analytics = get_analytics_service()
    
    # Get session info if available
    session = getattr(request.state, "session", None)
    user_id = session.user_id if session and session.is_authenticated else None
    session_id = session.session_id if session else None
    
    event = analytics.track(
        event_type=event_type,
        user_id=user_id,
        session_id=session_id,
        **body.properties
    )
    
    return {"status": "tracked", "event_id": event.id}


@router.get("/analytics/stats")
async def get_analytics_stats(request: Request):
    """
    Get analytics statistics.
    
    Returns event counts and top searches.
    """
    if not settings.FEATURE_ANALYTICS:
        raise HTTPException(status_code=503, detail="Analytics is disabled")
    
    analytics = get_analytics_service()
    return analytics.get_stats()


@router.get("/analytics/events")
async def get_recent_events(
    request: Request,
    event_type: Optional[str] = None,
    limit: int = 50
):
    """
    Get recent analytics events.
    
    Optionally filter by event type.
    """
    if not settings.FEATURE_ANALYTICS:
        raise HTTPException(status_code=503, detail="Analytics is disabled")
    
    analytics = get_analytics_service()
    
    filter_type = None
    if event_type:
        try:
            filter_type = EventType(event_type)
        except ValueError:
            pass
    
    events = analytics.get_recent_events(event_type=filter_type, limit=limit)
    return {"events": events, "count": len(events)}


# ==================== REFERRAL ENDPOINTS ====================

@router.get("/referral/code")
async def get_referral_code(
    request: Request,
    user_id: str = Depends(require_auth)
):
    """
    Get or create a referral code for the current user.
    """
    if not settings.FEATURE_REFERRALS:
        raise HTTPException(status_code=503, detail="Referrals are disabled")
    
    referrals = get_referral_service()
    
    # Check if user already has a code
    existing = referrals.get_user_code(user_id)
    if existing:
        code = existing
    else:
        code = referrals.generate_code(user_id)
    
    base_url = str(request.base_url).rstrip("/")
    referral_url = f"{base_url}/signup?ref={code.code}"
    
    return ReferralCodeResponse(
        code=code.code,
        uses=code.uses,
        max_uses=code.max_uses,
        expires_at=code.expires_at.isoformat() if code.expires_at else None,
        referral_url=referral_url
    )


@router.get("/referral/validate/{code}")
async def validate_referral_code(code: str):
    """
    Validate a referral code.
    """
    if not settings.FEATURE_REFERRALS:
        raise HTTPException(status_code=503, detail="Referrals are disabled")
    
    referrals = get_referral_service()
    referral_code = referrals.validate_code(code)
    
    if not referral_code:
        raise HTTPException(status_code=404, detail="Invalid or expired referral code")
    
    return {
        "valid": True,
        "code": referral_code.code,
        "remaining_uses": (referral_code.max_uses - referral_code.uses) if referral_code.max_uses else None
    }


@router.post("/referral/use/{code}")
async def use_referral_code(
    code: str,
    request: Request,
    user_id: str = Depends(require_auth)
):
    """
    Use a referral code (called during signup).
    """
    if not settings.FEATURE_REFERRALS:
        raise HTTPException(status_code=503, detail="Referrals are disabled")
    
    referrals = get_referral_service()
    referral = referrals.use_code(code, user_id)
    
    if not referral:
        raise HTTPException(status_code=400, detail="Could not use referral code")
    
    return {
        "status": "success",
        "referral_id": referral.id,
        "referrer_id": referral.referrer_id
    }


@router.get("/referral/stats")
async def get_referral_stats(
    request: Request,
    user_id: str = Depends(require_auth)
):
    """
    Get referral statistics for the current user.
    """
    if not settings.FEATURE_REFERRALS:
        raise HTTPException(status_code=503, detail="Referrals are disabled")
    
    referrals = get_referral_service()
    
    user_code = referrals.get_user_code(user_id)
    user_referrals = referrals.get_user_referrals(user_id)
    
    return {
        "code": user_code.code if user_code else None,
        "total_referrals": len(user_referrals),
        "referrals": [
            {
                "referred_id": r.referred_id,
                "created_at": r.created_at.isoformat(),
                "status": r.status
            }
            for r in user_referrals
        ]
    }


# ==================== SHAREABLE LINKS ENDPOINTS ====================

@router.post("/share/create")
async def create_share_link(
    body: CreateShareLinkRequest,
    request: Request
):
    """
    Create a shareable forecast link.
    """
    if not settings.FEATURE_SHAREABLE_LINKS:
        raise HTTPException(status_code=503, detail="Shareable links are disabled")
    
    links = get_shareable_link_service()
    
    # Get user ID if authenticated
    session = getattr(request.state, "session", None)
    user_id = session.user_id if session and session.is_authenticated else None
    
    link = links.create_link(
        lat=body.lat,
        lon=body.lon,
        location_name=body.location_name,
        expires_hours=body.expires_hours,
        created_by=user_id
    )
    
    base_url = str(request.base_url).rstrip("/")
    
    return ShareableLinkResponse(
        token=link.token,
        url=f"{base_url}/s/{link.token}",
        location_name=link.location_name,
        expires_at=link.expires_at.isoformat(),
        view_count=link.view_count
    )


@router.get("/share/{token}")
async def get_share_link(token: str, request: Request):
    """
    Get shareable link data.
    """
    if not settings.FEATURE_SHAREABLE_LINKS:
        raise HTTPException(status_code=503, detail="Shareable links are disabled")
    
    links = get_shareable_link_service()
    link = links.get_link(token)
    
    if not link:
        raise HTTPException(status_code=404, detail="Link not found or expired")
    
    return {
        "lat": link.lat,
        "lon": link.lon,
        "location_name": link.location_name,
        "created_at": link.created_at.isoformat(),
        "expires_at": link.expires_at.isoformat(),
        "view_count": link.view_count
    }


@router.get("/share/my/links")
async def get_my_share_links(
    request: Request,
    user_id: str = Depends(require_auth)
):
    """
    Get all shareable links created by the current user.
    """
    if not settings.FEATURE_SHAREABLE_LINKS:
        raise HTTPException(status_code=503, detail="Shareable links are disabled")
    
    links = get_shareable_link_service()
    user_links = links.get_user_links(user_id)
    
    base_url = str(request.base_url).rstrip("/")
    
    return {
        "links": [
            {
                "token": l.token,
                "url": f"{base_url}/s/{l.token}",
                "location_name": l.location_name,
                "created_at": l.created_at.isoformat(),
                "expires_at": l.expires_at.isoformat(),
                "view_count": l.view_count
            }
            for l in user_links
        ]
    }


# ==================== SOCIAL PREVIEW ENDPOINTS ====================

@router.get("/preview/meta")
async def get_social_preview_meta(
    request: Request,
    location: str,
    temperature: float,
    condition: str,
    icon: str = "🌤️",
    high: Optional[float] = None,
    low: Optional[float] = None
):
    """
    Get Open Graph meta tags for social sharing.
    """
    if not settings.FEATURE_SOCIAL_PREVIEW:
        raise HTTPException(status_code=503, detail="Social previews are disabled")
    
    preview = get_social_preview_service()
    
    data = SocialPreviewData(
        location=location,
        temperature=temperature,
        condition=condition,
        icon=icon,
        high=high,
        low=low
    )
    
    url = str(request.url)
    tags = preview.generate_meta_tags(data, url)
    
    return {
        "meta_tags": tags,
        "og_title": data.to_og_title(),
        "og_description": data.to_og_description()
    }


@router.get("/preview/image")
async def get_social_preview_image(
    request: Request,
    location: str,
    temperature: float,
    condition: str,
    icon: str = "🌤️",
    high: Optional[float] = None,
    low: Optional[float] = None
):
    """
    Get HTML for rendering social preview image.
    
    Use this with a headless browser (Puppeteer/Playwright) to generate preview images.
    """
    if not settings.FEATURE_SOCIAL_PREVIEW:
        raise HTTPException(status_code=503, detail="Social previews are disabled")
    
    preview = get_social_preview_service()
    
    data = SocialPreviewData(
        location=location,
        temperature=temperature,
        condition=condition,
        icon=icon,
        high=high,
        low=low
    )
    
    html = preview.generate_preview_html(data)
    
    return Response(content=html, media_type="text/html")
