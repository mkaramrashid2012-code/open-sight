"""Security module for OpenSight Private - Enterprise-grade authentication and authorization."""
import base64
from cryptography.fernet import Fernet
from app.core.config import settings


def get_encryption_key() -> bytes:
    """Get or derive encryption key from secret_key."""
    secret = settings.secret_key.encode()
    # Derive a 32-byte key from the secret using simple hashing
    import hashlib
    return base64.urlsafe_b64encode(hashlib.sha256(secret).digest())


def encrypt_rtsp_url(rtsp_url: str) -> str:
    """Encrypt an RTSP URL for secure storage."""
    f = Fernet(get_encryption_key())
    return f.encrypt(rtsp_url.encode()).decode()


def decrypt_rtsp_url(encrypted_url: str) -> str:
    """Decrypt an RTSP URL."""
    f = Fernet(get_encryption_key())
    return f.decrypt(encrypted_url.encode()).decode()


from app.security.auth import (
    User,
    UserCreate,
    Token,
    APIKeyInfo,
    verify_password,
    get_password_hash,
    generate_api_key,
    generate_access_token,
    verify_access_token,
    get_current_user_from_api_key,
    require_auth,
    require_superuser,
    audit_log,
    rate_limit,
    api_rate_limiter,
    auth_rate_limiter,
)

__all__ = [
    "User",
    "UserCreate",
    "Token",
    "APIKeyInfo",
    "verify_password",
    "get_password_hash",
    "generate_api_key",
    "generate_access_token",
    "verify_access_token",
    "get_current_user_from_api_key",
    "require_auth",
    "require_superuser",
    "audit_log",
    "rate_limit",
    "api_rate_limiter",
    "auth_rate_limiter",
    "encrypt_rtsp_url",
    "decrypt_rtsp_url",
]
