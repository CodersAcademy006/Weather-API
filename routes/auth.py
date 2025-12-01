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
from authlib.integrations.starlette_client import OAuth
from fastapi.responses import RedirectResponse
import secrets

logger = get_logger(__name__)

# Google OAuth setup
oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid_configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# Password hashing context
try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    # Test the context with a simple password
    test_hash = pwd_context.hash("test")
    logger.info("Bcrypt context initialized successfully")
except Exception as e:
    logger.warning(f"Bcrypt context failed, falling back to simpler hashing: {e}")
    import hashlib
    pwd_context = None

# Router
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ==================== TEST HELPER ====================

@router.post("/create-test-users")
async def create_test_users():
    """Create test users with known passwords for debugging."""
    storage = get_storage()
    
    test_users = [
        {"username": "admin", "email": "admin@test.com", "password": "Admin123!"},
        {"username": "user", "email": "user@test.com", "password": "User123!"},
        {"username": "demo", "email": "demo@test.com", "password": "Demo123!"}
    ]
    
    created = []
    for user_data in test_users:
        # Check if already exists
        existing = storage.get_user_by_email(user_data["email"])
        if not existing:
            hashed_password = hash_password(user_data["password"])
            user = User.create(
                username=user_data["username"],
                email=user_data["email"], 
                hashed_password=hashed_password
            )
            storage.create_user(user)
            created.append(user_data["username"])
    
    return {"created_users": created, "test_credentials": [
        "admin@test.com / Admin123!",
        "user@test.com / User123!", 
        "demo@test.com / Demo123!"
    ]}


# ==================== GOOGLE OAUTH ====================

@router.get("/google")
async def google_login(request: Request):
    """Redirect to Google OAuth."""
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, response: Response):
    """Handle Google OAuth callback."""
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to get user info from Google")
        
        email = user_info.get('email')
        name = user_info.get('name', email.split('@')[0])
        
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")
        
        storage = get_storage()
        
        # Check if user exists
        user = storage.get_user_by_email(email)
        
        if not user:
            # Create new user
            username = name.lower().replace(' ', '_')[:50]
            
            # Make username unique if it exists
            counter = 1
            original_username = username
            while storage.get_user_by_username(username):
                username = f"{original_username}_{counter}"
                counter += 1
            
            user = User.create(
                username=username,
                email=email,
                hashed_password="google_oauth"  # No password for OAuth users
            )
            storage.create_user(user)
            logger.info(f"Created new Google OAuth user: {email}")
        
        # Create session
        session_middleware = get_session_middleware()
        if session_middleware:
            session_middleware.create_session(user.user_id, response)
        
        logger.info(f"Google OAuth login successful: {email}")
        
        # Redirect to dashboard or home page
        return RedirectResponse(url="/weather-dashboard.html")
        
    except Exception as e:
        logger.error(f"Google OAuth error: {e}")
        raise HTTPException(status_code=400, detail=f"OAuth authentication failed: {str(e)}")


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
    """Hash a password using bcrypt or fallback to SHA-256."""
    if pwd_context is not None:
        try:
            # Truncate password to 72 bytes to comply with bcrypt limitations
            password_bytes = password.encode('utf-8', errors='ignore')[:72]
            truncated_password = password_bytes.decode('utf-8', errors='ignore')
            return pwd_context.hash(truncated_password)
        except Exception as e:
            logger.warning(f"Bcrypt hashing failed, using fallback: {e}")
    
    # Fallback to SHA-256 with salt
    import hashlib
    import secrets
    salt = secrets.token_hex(16)
    hash_obj = hashlib.sha256((password + salt).encode('utf-8'))
    return f"sha256${salt}${hash_obj.hexdigest()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    if pwd_context is not None and not hashed_password.startswith('sha256$'):
        try:
            password_bytes = plain_password.encode('utf-8', errors='ignore')[:72]
            truncated_password = password_bytes.decode('utf-8', errors='ignore')
            return pwd_context.verify(truncated_password, hashed_password)
        except Exception as e:
            logger.warning(f"Bcrypt verification failed: {e}")
            return False
    
    # Handle SHA-256 fallback
    if hashed_password.startswith('sha256$'):
        try:
            import hashlib
            parts = hashed_password.split('$')
            if len(parts) != 3:
                return False
            _, salt, stored_hash = parts
            hash_obj = hashlib.sha256((plain_password + salt).encode('utf-8'))
            return hash_obj.hexdigest() == stored_hash
        except Exception as e:
            logger.error(f"SHA-256 verification failed: {e}")
            return False
    
    return False


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
    try:
        session_data = get_session(request)
        
        if not session_data.is_authenticated or not session_data.session:
            # Clear any existing cookies even if no valid session
            session_middleware = get_session_middleware()
            if session_middleware:
                # Delete cookie by setting it with expired date
                response.delete_cookie(
                    key=session_middleware.cookie_name,
                    httponly=session_middleware.cookie_httponly,
                    secure=session_middleware.cookie_secure,
                    samesite=session_middleware.cookie_samesite
                )
            
            return AuthResponse(
                success=True,
                message="No active session"
            )
        
        # Destroy session
        session_middleware = get_session_middleware()
        if session_middleware:
            session_middleware.destroy_session(session_data.session.session_id, response)
        
        logger.info(f"User logged out: {session_data.user_id}")
        
        return AuthResponse(
            success=True,
            message="Logged out successfully"
        )
    
    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        # Still try to clear the cookie in case of error
        session_middleware = get_session_middleware()
        if session_middleware:
            response.delete_cookie(
                key=session_middleware.cookie_name,
                httponly=session_middleware.cookie_httponly,
                secure=session_middleware.cookie_secure,
                samesite=session_middleware.cookie_samesite
            )
        
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
