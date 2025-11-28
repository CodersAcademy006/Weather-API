"""
Authentication Routes

This module provides endpoints for:
- User signup
- User login
- User logout
- Session management
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Request, Response, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr, Field, field_validator
from passlib.context import CryptContext
from storage import get_storage, User, SearchHistory
from session_middleware import (
    get_session,
    require_auth,
    get_session_middleware,
    SessionData
)
from config import settings
from logging_config import get_logger

logger = get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Router
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ==================== PYDANTIC MODELS ====================

class SignupRequest(BaseModel):
    """Request model for user signup."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    
    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        return v.lower()
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    """Request model for user login."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Response model for user data."""
    user_id: str
    username: str
    email: str
    created_at: str
    is_active: bool


class AuthResponse(BaseModel):
    """Response model for authentication."""
    success: bool
    message: str
    user: Optional[UserResponse] = None


class SearchHistoryRequest(BaseModel):
    """Request model for adding search history."""
    query: str
    lat: float
    lon: float


class SearchHistoryResponse(BaseModel):
    """Response model for search history."""
    id: str
    query: str
    lat: float
    lon: float
    searched_at: str


# ==================== HELPER FUNCTIONS ====================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ==================== ENDPOINTS ====================

@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: Request, response: Response, data: SignupRequest):
    """
    Register a new user account.
    
    - **username**: Unique username (3-50 characters)
    - **email**: Valid email address
    - **password**: Strong password (8+ characters with mixed case and numbers)
    """
    storage = get_storage()
    
    # Check if email already exists
    existing_user = storage.get_user_by_email(data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username already exists
    existing_user = storage.get_user_by_username(data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create user
    hashed_password = hash_password(data.password)
    user = User.create(
        username=data.username,
        email=data.email,
        hashed_password=hashed_password
    )
    
    try:
        storage.create_user(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Create session
    session_middleware = get_session_middleware()
    if session_middleware:
        session_middleware.create_session(user.user_id, response)
    
    logger.info(f"User registered: {user.username}")
    
    return AuthResponse(
        success=True,
        message="Account created successfully",
        user=UserResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            created_at=user.created_at,
            is_active=user.is_active
        )
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: Request, response: Response, data: LoginRequest):
    """
    Authenticate a user and create a session.
    
    - **email**: Registered email address
    - **password**: Account password
    """
    storage = get_storage()
    
    # Find user by email
    user = storage.get_user_by_email(data.email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    # Create session
    session_middleware = get_session_middleware()
    if session_middleware:
        session_middleware.create_session(user.user_id, response)
    
    logger.info(f"User logged in: {user.username}")
    
    return AuthResponse(
        success=True,
        message="Login successful",
        user=UserResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            created_at=user.created_at,
            is_active=user.is_active
        )
    )


@router.post("/logout", response_model=AuthResponse)
async def logout(request: Request, response: Response):
    """
    Log out the current user and invalidate the session.
    """
    session_data = get_session(request)
    
    if not session_data.is_authenticated:
        return AuthResponse(
            success=True,
            message="No active session"
        )
    
    # Destroy session
    session_middleware = get_session_middleware()
    if session_middleware and session_data.session:
        session_middleware.destroy_session(session_data.session.session_id, response)
    
    logger.info(f"User logged out: {session_data.user_id}")
    
    return AuthResponse(
        success=True,
        message="Logged out successfully"
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    request: Request,
    session: SessionData = Depends(require_auth)
):
    """
    Get the current authenticated user's information.
    
    Requires authentication.
    """
    storage = get_storage()
    user = storage.get_user_by_id(session.user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        created_at=user.created_at,
        is_active=user.is_active
    )


@router.get("/session")
async def get_session_info(request: Request):
    """
    Get current session information.
    
    Returns session status and expiration info if authenticated.
    """
    session_data = get_session(request)
    
    if not session_data.is_authenticated:
        return {
            "authenticated": False,
            "message": "No active session"
        }
    
    return {
        "authenticated": True,
        "user_id": session_data.user_id,
        "session_id": session_data.session.session_id if session_data.session else None,
        "expires_at": session_data.session.expires_at if session_data.session else None
    }


@router.post("/search-history", response_model=SearchHistoryResponse)
async def add_search_history(
    request: Request,
    data: SearchHistoryRequest,
    session: SessionData = Depends(require_auth)
):
    """
    Add a search to the user's history.
    
    Requires authentication.
    """
    storage = get_storage()
    
    entry = SearchHistory.create(
        user_id=session.user_id,
        query=data.query,
        lat=data.lat,
        lon=data.lon
    )
    
    storage.add_search_history(entry)
    
    return SearchHistoryResponse(
        id=entry.id,
        query=entry.query,
        lat=entry.lat,
        lon=entry.lon,
        searched_at=entry.searched_at
    )


@router.get("/search-history", response_model=list[SearchHistoryResponse])
async def get_search_history(
    request: Request,
    limit: int = 10,
    session: SessionData = Depends(require_auth)
):
    """
    Get the user's search history.
    
    Requires authentication.
    """
    storage = get_storage()
    
    history = storage.get_user_search_history(session.user_id, limit)
    
    return [
        SearchHistoryResponse(
            id=entry.id,
            query=entry.query,
            lat=entry.lat,
            lon=entry.lon,
            searched_at=entry.searched_at
        )
        for entry in history
    ]
