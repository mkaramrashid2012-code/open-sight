"""Authentication API endpoints for enterprise-grade security."""
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.security.auth import (
    User,
    UserCreate,
    Token,
    APIKeyInfo,
    generate_api_key,
    generate_access_token,
    get_password_hash,
    require_auth,
    audit_log,
    rate_limit,
    auth_rate_limiter,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


# In-memory user store for prototype - replace with database in production
_users_store: dict[str, dict] = {}
_api_keys_store: dict[str, dict] = {}


@router.post("/register", response_model=User, status_code=201)
@rate_limit(auth_rate_limiter)
async def register_user(payload: UserCreate, request: Request):
    """Register a new user account."""
    # Check if username exists
    if payload.username in _users_store:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )
    
    # Create user
    user_id = uuid4()
    user_data = {
        "id": str(user_id),
        "username": payload.username,
        "full_name": payload.full_name,
        "password_hash": get_password_hash(payload.password),
        "is_active": True,
        "is_superuser": payload.is_superuser,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _users_store[payload.username] = user_data
    
    audit_log("user_register", User(id=user_id, username=payload.username), "user", {"username": payload.username})
    
    return User(
        id=user_id,
        username=payload.username,
        full_name=payload.full_name,
        is_active=True,
        is_superuser=payload.is_superuser,
    )


@router.post("/login", response_model=Token)
@rate_limit(auth_rate_limiter)
async def login(payload: UserCreate, request: Request):
    """Authenticate user and return access token."""
    # Find user
    user_data = _users_store.get(payload.username)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    if not pwd_context.verify(payload.password, user_data["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if active
    if not user_data.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    user_id = UUID(user_data["id"])
    
    # Generate token
    access_token = generate_access_token(user_id, payload.username, expires_hours=24)
    
    audit_log("user_login", User(id=user_id, username=payload.username), "user")
    
    return Token(access_token=access_token, token_type="bearer", expires_in=86400)


@router.post("/api-keys", response_model=APIKeyInfo)
async def create_api_key(
    request: Request,
    name: str = "Default API Key",
    expires_days: int = 365,
    user: User = Depends(require_auth),
):
    """Generate a new API key for the authenticated user."""
    api_key = generate_api_key()
    expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days) if expires_days else None
    
    key_data = {
        "key": api_key,
        "user_id": str(user.id),
        "name": name,
        "created_at": datetime.now(timezone.utc),
        "expires_at": expires_at,
        "is_active": True,
        "permissions": ["read", "write"],
    }
    _api_keys_store[api_key] = key_data
    
    audit_log("api_key_create", user, "api_key", {"name": name})
    
    return APIKeyInfo(
        key=api_key,
        user_id=user.id,
        name=name,
        created_at=key_data["created_at"],
        expires_at=expires_at,
        is_active=True,
        permissions=key_data["permissions"],
    )


@router.get("/me", response_model=User)
async def get_current_user_info(user: User = Depends(require_auth)):
    """Get current authenticated user information."""
    return user


@router.post("/logout")
async def logout(request: Request, user: User = Depends(require_auth)):
    """Logout current user (invalidate token on client side)."""
    audit_log("user_logout", user, "user")
    return {"status": "logged_out"}


@router.get("/api-keys", response_model=list[APIKeyInfo])
async def list_api_keys(user: User = Depends(require_auth)):
    """List all API keys for the current user."""
    user_keys = [k for k in _api_keys_store.values() if k["user_id"] == str(user.id)]
    return [
        APIKeyInfo(
            key=k["key"],
            user_id=UUID(k["user_id"]),
            name=k["name"],
            created_at=k["created_at"],
            expires_at=k["expires_at"],
            is_active=k["is_active"],
            permissions=k["permissions"],
        )
        for k in user_keys
    ]


@router.delete("/api-keys/{api_key}")
async def revoke_api_key(api_key: str, user: User = Depends(require_auth)):
    """Revoke an API key."""
    if api_key not in _api_keys_store:
        raise HTTPException(status_code=404, detail="API key not found")
    
    key_data = _api_keys_store[api_key]
    if key_data["user_id"] != str(user.id) and not user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to revoke this key")
    
    del _api_keys_store[api_key]
    audit_log("api_key_revoke", user, "api_key", {"key": api_key[:10] + "..."})
    
    return {"status": "revoked"}
