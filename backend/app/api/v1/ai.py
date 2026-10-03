from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_project_for_user
from app.db.session import get_db
from app.models.project import Project
from app.services.ai_analyst import (
    analyze_project_health,
    AIHealthAnalysisResponse,
)

router = APIRouter(prefix="/projects/{project_id}/ai", tags=["AI Telemetry Intelligence"])


@router.get(
    "/insights",
    response_model=AIHealthAnalysisResponse,
    summary="Generate AI Incident Diagnosis & Telemetry Health",
    description="Analyzes live error bursts, clusters failure signatures, identifies component bottlenecks, and provides root cause analysis (RCA) and mitigation runbooks.",
)
def get_ai_insights(
    project: Project = Depends(get_project_for_user),
    window_minutes: int = Query(30, ge=1, le=1440, description="Analysis window in minutes"),
    db: Session = Depends(get_db),
):
    return analyze_project_health(db=db, project_id=project.id, window_minutes=window_minutes)


@router.post(
    "/analyze",
    response_model=AIHealthAnalysisResponse,
    summary="Trigger On-Demand AI Root Cause Analysis",
    description="Forces immediate re-evaluation of all telemetry clusters for the active project.",
)
def trigger_ai_analysis(
    project: Project = Depends(get_project_for_user),
    window_minutes: int = Query(30, ge=1, le=1440, description="Analysis window in minutes"),
    db: Session = Depends(get_db),
):
    return analyze_project_health(db=db, project_id=project.id, window_minutes=window_minutes)
