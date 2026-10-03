import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union
import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.now(timezone.utc),
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except (jwt.PyJWTError, Exception):
        return None


def generate_api_key() -> tuple[str, str, str]:
    """
    Generates a new API key.
    Returns:
        (raw_key, key_prefix, key_hash)
        raw_key: e.g. "pw_live_6f4b8a21..." (shown only once to user)
        key_prefix: e.g. "pw_live_6f4b" (for identification)
        key_hash: sha256 hex digest (for database lookup)
    """
    random_part = secrets.token_hex(24)
    raw_key = f"pw_live_{random_part}"
    key_prefix = raw_key[:12]
    key_hash = hash_api_key(raw_key)
    return raw_key, key_prefix, key_hash


def hash_api_key(raw_key: str) -> str:
    """Computes SHA-256 hash of API key for secure storage & fast indexed lookup."""
    return hashlib.sha256(raw_key.strip().encode("utf-8")).hexdigest()
