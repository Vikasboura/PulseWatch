from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_project_for_user
from app.core.security import generate_api_key
from app.db.session import get_db
from app.models.user import User
from app.models.project import Project, ApiKey
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ApiKeyCreate,
    ApiKeyResponse,
    ApiKeyCreatedResponse,
)

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=List[ProjectResponse])
def list_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all monitoring projects belonging to the logged-in user."""
    return db.query(Project).filter(Project.user_id == current_user.id).order_by(Project.created_at.desc()).all()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project_in: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new project."""
    project = Project(
        user_id=current_user.id,
        name=project_in.name,
        description=project_in.description,
        retention_days=project_in.retention_days,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project: Project = Depends(get_project_for_user)):
    """Get project details."""
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_in: ProjectUpdate,
    project: Project = Depends(get_project_for_user),
    db: Session = Depends(get_db),
):
    """Update project metadata or retention period."""
    if project_in.name is not None:
        project.name = project_in.name
    if project_in.description is not None:
        project.description = project_in.description
    if project_in.retention_days is not None:
        project.retention_days = project_in.retention_days
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project: Project = Depends(get_project_for_user),
    db: Session = Depends(get_db),
):
    """Delete a project and cascade-delete all its logs, metrics, alerts, and API keys."""
    db.delete(project)
    db.commit()
    return None


# --- API Key Management ---

@router.get("/{project_id}/api-keys", response_model=List[ApiKeyResponse])
def list_api_keys(
    project: Project = Depends(get_project_for_user),
    db: Session = Depends(get_db),
):
    """List all API keys for a project (never returns secret hash or raw key)."""
    return db.query(ApiKey).filter(ApiKey.project_id == project.id).order_by(ApiKey.created_at.desc()).all()


@router.post("/{project_id}/api-keys", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_api_key_for_project(
    key_in: ApiKeyCreate,
    project: Project = Depends(get_project_for_user),
    db: Session = Depends(get_db),
):
    """
    Generate a new API key for the project.
    IMPORTANT: The `raw_key` is only returned once in this response and cannot be retrieved again.
    """
    raw_key, key_prefix, key_hash = generate_api_key()
    api_key = ApiKey(
        project_id=project.id,
        name=key_in.name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        is_active=True,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    return ApiKeyCreatedResponse(
        id=api_key.id,
        project_id=api_key.project_id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        is_active=api_key.is_active,
        last_used_at=api_key.last_used_at,
        created_at=api_key.created_at,
        raw_key=raw_key,
    )


@router.delete("/{project_id}/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: str,
    project: Project = Depends(get_project_for_user),
    db: Session = Depends(get_db),
):
    """Revoke/delete an API key."""
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.project_id == project.id).first()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API Key not found",
        )
    db.delete(api_key)
    db.commit()
    return None
