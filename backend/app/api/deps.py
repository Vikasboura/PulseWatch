import time
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlalchemy.orm import Session

from app.core.security import decode_access_token, hash_api_key
from app.db.session import get_db
from app.models.user import User
from app.models.project import Project, ApiKey

jwt_bearer = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# In-memory throttle tracker for last_used_at updates: api_key_id -> unix_epoch
_last_used_throttle: dict[str, float] = {}


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(jwt_bearer),
    db: Session = Depends(get_db)
) -> User:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


def get_project_for_user(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you do not have permission to access it",
        )
    return project


def get_api_key_project(
    header_key: Optional[str] = Security(api_key_header),
    bearer_creds: Optional[HTTPAuthorizationCredentials] = Security(jwt_bearer),
    db: Session = Depends(get_db)
) -> tuple[Project, ApiKey]:
    """
    Authenticates ingestion requests via API key (passed via X-API-Key header or Bearer token).
    Throttles last_used_at database updates to once per minute per key.
    """
    raw_key = None
    if header_key:
        raw_key = header_key.strip()
    elif bearer_creds and bearer_creds.credentials:
        # Check if the bearer token is actually an API key (e.g., pw_live_...)
        raw_key = bearer_creds.credentials.strip()

    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key. Provide 'X-API-Key' header or 'Bearer pw_live_...'",
        )

    key_hash = hash_api_key(raw_key)
    api_key = db.query(ApiKey).filter(ApiKey.key_hash == key_hash, ApiKey.is_active == True).first()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API Key",
        )

    # Throttled update of last_used_at (at most once every 60 seconds)
    now_epoch = time.time()
    last_synced = _last_used_throttle.get(api_key.id, 0.0)
    if now_epoch - last_synced > 60.0:
        _last_used_throttle[api_key.id] = now_epoch
        api_key.last_used_at = datetime.now(timezone.utc)
        db.commit()

    return api_key.project, api_key
