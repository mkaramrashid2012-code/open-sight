"""Enterprise-grade authentication and authorization system."""
import hashlib
import hmac
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Optional
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# API Key header
api_key_header = APIKeyHeader(name=settings.api_key_header, auto_error=False)


class User(BaseModel):
    """User model for authentication."""
    id: UUID
    username: str
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None
    api_key: Optional[str] = None


class UserCreate(BaseModel):
    """User creation schema."""
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = None
    is_superuser: bool = False


class Token(BaseModel):
    """Authentication token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class APIKeyInfo(BaseModel):
    """API Key information."""
    key: str
    user_id: UUID
    name: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True
    last_used: Optional[datetime] = None
    permissions: list[str] = Field(default_factory=list)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def generate_api_key() -> str:
    """Generate a secure API key."""
    return f"os_{secrets.token_urlsafe(32)}"


def generate_access_token(user_id: UUID, username: str, expires_hours: int = 24) -> str:
    """
    Generate a secure access token.
    
    In production, replace with JWT tokens. For now, use HMAC-signed tokens.
    """
    if not settings.secret_key or settings.secret_key == "dev-secret-key-change-in-production":
        logger.warning("Using default secret key - change in production!")
    
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
    payload = f"{user_id}:{username}:{int(expires_at.timestamp())}"
    signature = hmac.new(
        settings.secret_key.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return f"{payload}:{signature}"


def verify_access_token(token: str) -> Optional[dict]:
    """Verify and decode an access token."""
    try:
        parts = token.rsplit(":", 1)
        if len(parts) != 2:
            return None
        
        payload, signature = parts
        expected_signature = hmac.new(
            settings.secret_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return None
        
        payload_parts = payload.split(":")
        if len(payload_parts) != 3:
            return None
        
        user_id, username, exp_timestamp = payload_parts
        expires_at = datetime.fromtimestamp(int(exp_timestamp), tz=timezone.utc)
        
        if datetime.now(timezone.utc) > expires_at:
            return None
        
        return {
            "user_id": UUID(user_id),
            "username": username,
            "expires_at": expires_at,
        }
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        return None


async def get_current_user_from_api_key(
    request: Request,
    api_key: Optional[str] = Depends(api_key_header),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Authenticate user from API key.
    
    For enterprise deployment, implement proper user database.
    This is a simplified version for local deployment.
    """
    if not api_key:
        return None
    
    # In production, validate against database
    # For now, accept any valid-format API key if allow_anonymous
    if settings.allow_anonymous and api_key.startswith("os_"):
        return User(
            id=uuid4(),
            username="anonymous",
            is_active=True,
        )
    
    # Validate API key format
    if not api_key.startswith("os_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
            headers={"WWW-Authenticate": settings.api_key_header},
        )
    
    # TODO: Validate against database in production
    return User(
        id=uuid4(),
        username="api_user",
        is_active=True,
    )


async def require_auth(
    request: Request,
    user: Optional[User] = Depends(get_current_user_from_api_key),
) -> User:
    """Require authentication for endpoint."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": settings.api_key_header},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    return user


async def require_superuser(
    user: User = Depends(require_auth),
) -> User:
    """Require superuser privileges."""
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required",
        )
    return user


def audit_log(action: str, user: Optional[User], resource: str, details: Optional[dict] = None):
    """Log audit trail for sensitive operations."""
    if not settings.enable_audit_logging:
        return
    
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "user_id": str(user.id) if user else "anonymous",
        "username": user.username if user else "anonymous",
        "resource": resource,
        "details": details or {},
        "ip_address": None,  # Set from request if available
    }
    
    logger.info(f"AUDIT: {log_entry}")


class RateLimiter:
    """Simple in-memory rate limiter for API endpoints."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed for given key."""
        now = time.time()
        window_start = now - self.window_seconds
        
        if key not in self._requests:
            self._requests[key] = []
        
        # Clean old requests
        self._requests[key] = [t for t in self._requests[key] if t > window_start]
        
        if len(self._requests[key]) >= self.max_requests:
            return False
        
        self._requests[key].append(now)
        return True
    
    def get_retry_after(self, key: str) -> int:
        """Get seconds until next request is allowed."""
        if key not in self._requests or not self._requests[key]:
            return 0
        
        oldest = min(self._requests[key])
        return max(0, int(oldest + self.window_seconds - time.time()))


# Global rate limiters
api_rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
auth_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)


def rate_limit(limiter: RateLimiter = api_rate_limiter):
    """Decorator for rate limiting endpoints."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            client_ip = request.client.host if request.client else "unknown"
            key = f"{func.__name__}:{client_ip}"
            
            if not limiter.is_allowed(key):
                retry_after = limiter.get_retry_after(key)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                    headers={"Retry-After": str(retry_after)},
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
