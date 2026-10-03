import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import delete

from app.models.project import Project
from app.models.log_record import LogRecord
from app.models.metric_record import MetricRecord

logger = logging.getLogger(__name__)


def purge_expired_records(db: Session, project_id: str = None) -> Dict[str, Any]:
    """
    Deletes logs and metrics older than the retention_days defined on the project.
    Can be run for a single project or across all projects.
    """
    now = datetime.now(timezone.utc)
    results = {
        "projects_processed": 0,
        "logs_purged": 0,
        "metrics_purged": 0,
    }

    query = db.query(Project)
    if project_id:
        query = query.filter(Project.id == project_id)
    projects = query.all()

    for proj in projects:
        cutoff = now - timedelta(days=proj.retention_days)
        
        # Purge logs older than cutoff
        deleted_logs = db.query(LogRecord).filter(
            LogRecord.project_id == proj.id,
            LogRecord.timestamp < cutoff
        ).delete(synchronize_session=False)

        # Purge metrics older than cutoff
        deleted_metrics = db.query(MetricRecord).filter(
            MetricRecord.project_id == proj.id,
            MetricRecord.timestamp < cutoff
        ).delete(synchronize_session=False)

        db.commit()

        results["projects_processed"] += 1
        results["logs_purged"] += deleted_logs
        results["metrics_purged"] += deleted_metrics

    logger.info(
        f"Data retention cleanup completed: {results['projects_processed']} projects, "
        f"{results['logs_purged']} logs deleted, {results['metrics_purged']} metrics deleted."
    )
    return results
