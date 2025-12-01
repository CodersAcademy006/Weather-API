"""
Secure Session Middleware

This module provides server-side session management with:
- UUID session IDs
- CSV-based session storage
- Session timeout management
- Secure cookie handling
- Request-attached session objects
"""

from datetime import datetime, timezone
from typing import Optional, Callable
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from storage import get_storage, Session
from config import settings
from logging_config import get_logger

logger = get_logger(__name__)


class SessionData:
    """
    Session data container attached to requests.
    """
    
    def __init__(
        self,
        session: Optional[Session] = None,
        user_id: Optional[str] = None,
        is_authenticated: bool = False
    ):
        self.session = session
        self.user_id = user_id
        self.is_authenticated = is_authenticated
        self._modified = False
    
    def mark_modified(self) -> None:
        """Mark session as modified (needs to be saved)."""
        self._modified = True
    
    @property
    def is_modified(self) -> bool:
        """Check if session has been modified."""
        return self._modified


class SessionMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for session management.
    
    Handles:
    - Session ID extraction from cookies
    - Session validation
    - Session data attachment to requests
    - Cookie management
    """
    
    def __init__(
        self,
        app,
        cookie_name: str = None,
        cookie_secure: bool = None,
        cookie_httponly: bool = None,
        cookie_samesite: str = None,
        session_timeout: int = None
    ):
        super().__init__(app)
        self.cookie_name = cookie_name or settings.SESSION_COOKIE_NAME
        self.cookie_secure = cookie_secure if cookie_secure is not None else settings.SESSION_COOKIE_SECURE
        self.cookie_httponly = cookie_httponly if cookie_httponly is not None else settings.SESSION_COOKIE_HTTPONLY
        self.cookie_samesite = cookie_samesite or settings.SESSION_COOKIE_SAMESITE
        self.session_timeout = session_timeout or settings.SESSION_TIMEOUT_SECONDS
        
        # Auto-register this instance globally
        set_session_middleware(self)
        
        logger.info(
            f"Session middleware initialized (cookie={self.cookie_name}, "
            f"secure={self.cookie_secure}, timeout={self.session_timeout}s)"
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with session handling."""
        storage = get_storage()
        session_data = SessionData()
        
        # Extract session ID from cookie
        session_id = request.cookies.get(self.cookie_name)
        
        if session_id:
            # Load existing session
            session = storage.get_session(session_id)
            
            if session and session.is_valid and not session.is_expired():
                # Valid session found
                session_data.session = session
                session_data.user_id = session.user_id
                session_data.is_authenticated = True
                
                # Update last_active_at
                session.last_active_at = datetime.now(timezone.utc).isoformat()
                storage.update_session(session)
                
                logger.debug(f"Session loaded for user: {session.user_id}")
        
        # Attach session data to request state
        request.state.session = session_data
        
        # Process the request
        response = await call_next(request)
        
        return response
    
    def create_session(self, user_id: str, response: Response) -> Session:
        """
        Create a new session for a user and set the cookie.
        
        Args:
            user_id: The user ID to create session for
            response: The response object to set cookie on
            
        Returns:
            The created Session object
        """
        storage = get_storage()
        
        # Create new session
        session = Session.create(user_id, self.session_timeout)
        storage.create_session(session)
        
        # Set cookie
        response.set_cookie(
            key=self.cookie_name,
            value=session.session_id,
            httponly=self.cookie_httponly,
            secure=self.cookie_secure,
            samesite=self.cookie_samesite,
            max_age=self.session_timeout
        )
        
        logger.info(f"Session created for user: {user_id}")
        return session
    
    def destroy_session(self, session_id: str, response: Response) -> bool:
        """
        Destroy a session and clear the cookie.
        
        Args:
            session_id: The session ID to destroy
            response: The response object to clear cookie on
            
        Returns:
            True if session was destroyed, False otherwise
        """
        storage = get_storage()
        
        # Invalidate session in storage
        result = storage.invalidate_session(session_id)
        
        # Clear cookie
        response.delete_cookie(
            key=self.cookie_name,
            httponly=self.cookie_httponly,
            secure=self.cookie_secure,
            samesite=self.cookie_samesite
        )
        
        if result:
            logger.info(f"Session destroyed: {session_id}")
        
        return result


def get_session(request: Request) -> SessionData:
    """
    Get the session data from a request.
    
    Args:
        request: The FastAPI request object
        
    Returns:
        SessionData object
        
    Raises:
        HTTPException: If session middleware is not configured
    """
    if not hasattr(request.state, "session"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session middleware not configured"
        )
    
    return request.state.session


def require_auth(request: Request) -> SessionData:
    """
    Require authentication for an endpoint.
    
    Use as a FastAPI dependency to protect endpoints.
    
    Args:
        request: The FastAPI request object
        
    Returns:
        SessionData object if authenticated
        
    Raises:
        HTTPException: If not authenticated
    """
    session = get_session(request)
    
    if not session.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return session


def optional_auth(request: Request) -> SessionData:
    """
    Optional authentication for an endpoint.
    
    Returns session data regardless of authentication status.
    
    Args:
        request: The FastAPI request object
        
    Returns:
        SessionData object
    """
    return get_session(request)


# Global session middleware instance
_session_middleware: Optional[SessionMiddleware] = None


def get_session_middleware() -> Optional[SessionMiddleware]:
    """Get the global session middleware instance."""
    return _session_middleware


def set_session_middleware(middleware: SessionMiddleware) -> None:
    """Set the global session middleware instance."""
    global _session_middleware
    _session_middleware = middleware
