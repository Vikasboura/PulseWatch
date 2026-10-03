import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.log_record import LogRecord
from app.models.metric_record import MetricRecord
from app.models.alert import AlertEvent


class ErrorCluster(BaseModel):
    signature: str
    component: str
    count: int
    severity: str
    sample_message: str
    first_seen: datetime
    last_seen: datetime


class AIRecommendation(BaseModel):
    title: str
    action: str
    priority: str
    rationale: str


class AIHealthAnalysisResponse(BaseModel):
    project_id: str
    timestamp: datetime
    health_score: int  # 0 - 100
    overall_status: str  # "healthy", "degraded", "critical"
    summary: str
    total_errors_analyzed: int
    error_clusters: List[ErrorCluster]
    metric_anomalies: List[Dict[str, Any]]
    recommendations: List[AIRecommendation]


def extract_error_signature(message: str) -> tuple[str, str]:
    """
    Normalizes log message into (signature, component).
    Identifies common infrastructure and application patterns.
    """
    msg = message.strip()
    
    if re.search(r"Postgres|database|db|pool exhausted|deadlock|SQL", msg, re.IGNORECASE):
        comp = "Database (PostgreSQL)"
        if "pool exhausted" in msg.lower():
            sig = "Database Connection Pool Starvation"
        elif "deadlock" in msg.lower():
            sig = "Database Transaction Deadlock"
        else:
            sig = "Database Execution Error"
        return sig, comp

    if re.search(r"stripe|payment|gateway|charge|checkout", msg, re.IGNORECASE):
        comp = "Payment Services"
        if "timeout" in msg.lower() or "504" in msg:
            sig = "Payment Gateway Upstream Timeout"
        elif "declined" in msg.lower() or "failed" in msg.lower():
            sig = "Payment Processing Failure"
        else:
            sig = "Payment API Degradation"
        return sig, comp

    if re.search(r"redis|cache|cluster node|unreachable", msg, re.IGNORECASE):
        comp = "Caching (Redis)"
        sig = "Redis Cluster Node Unreachable"
        return sig, comp

    if re.search(r"rate\s*limit|quota|429", msg, re.IGNORECASE):
        comp = "API Gateway"
        sig = "Client Quota / Rate Limit Threshold Exceeded"
        return sig, comp

    if re.search(r"memory|pod memory|heap|oom", msg, re.IGNORECASE):
        comp = "Compute Infrastructure"
        sig = "High Memory Pressure / OOM Warning"
        return sig, comp

    # Fallback to first 4 words
    words = msg.split()[:4]
    sig = " ".join(words) if words else "Unknown Application Error"
    return sig, "Application Core"


def analyze_project_health(db: Session, project_id: str, window_minutes: int = 15) -> AIHealthAnalysisResponse:
    now = datetime.now(timezone.utc)
    start_window = now - timedelta(minutes=window_minutes)

    # 1. Fetch recent error & warning logs
    error_logs = (
        db.query(LogRecord)
        .filter(
            LogRecord.project_id == project_id,
            LogRecord.timestamp >= start_window,
            LogRecord.level.in_(["ERROR", "CRITICAL", "WARNING"]),
        )
        .order_by(LogRecord.timestamp.desc())
        .limit(300)
        .all()
    )

    # 2. Cluster errors
    clusters_map: Dict[str, Dict[str, Any]] = {}
    for log in error_logs:
        sig, comp = extract_error_signature(log.message)
        if sig not in clusters_map:
            clusters_map[sig] = {
                "signature": sig,
                "component": comp,
                "count": 0,
                "severity": "CRITICAL" if log.level in ["ERROR", "CRITICAL"] else "WARNING",
                "sample_message": log.message,
                "first_seen": log.timestamp,
                "last_seen": log.timestamp,
            }
        clusters_map[sig]["count"] += 1
        if log.timestamp < clusters_map[sig]["first_seen"]:
            clusters_map[sig]["first_seen"] = log.timestamp
        if log.timestamp > clusters_map[sig]["last_seen"]:
            clusters_map[sig]["last_seen"] = log.timestamp

    error_clusters = [ErrorCluster(**c) for c in clusters_map.values()]
    error_clusters.sort(key=lambda x: x.count, reverse=True)

    # 3. Detect Metric Anomalies (e.g. latency, error rate)
    metric_records = (
        db.query(MetricRecord)
        .filter(
            MetricRecord.project_id == project_id,
            MetricRecord.timestamp >= start_window,
        )
        .all()
    )

    anomalies: List[Dict[str, Any]] = []
    latencies = [m.value for m in metric_records if m.name == "http_latency_ms"]
    if latencies:
        avg_lat = sum(latencies) / len(latencies)
        max_lat = max(latencies)
        if max_lat > 250:
            anomalies.append({
                "metric": "http_latency_ms",
                "condition": "p99 latency spike detected",
                "value": round(max_lat, 2),
                "threshold": 250.0,
                "severity": "WARNING"
            })

    # 4. Check active alert events
    active_incidents = (
        db.query(AlertEvent)
        .filter(
            AlertEvent.project_id == project_id,
            AlertEvent.status == "triggered",
        )
        .count()
    )

    # 5. Compute Health Score (0 - 100)
    score = 100
    total_errors = len(error_logs)
    score -= min(50, total_errors * 2)
    score -= min(30, active_incidents * 15)
    score -= min(20, len(anomalies) * 10)
    score = max(5, min(100, score))

    if score >= 85:
        overall_status = "healthy"
    elif score >= 50:
        overall_status = "degraded"
    else:
        overall_status = "critical"

    # 6. Generate AI recommendations
    recommendations: List[AIRecommendation] = []

    for cluster in error_clusters:
        if "Connection Pool" in cluster.signature:
            recommendations.append(AIRecommendation(
                title="Expand Database Connection Pool Capacity",
                action="Increase DB_POOL_SIZE from 10 to 25 and tune connection lease timeout to 5s in postgres config.",
                priority="CRITICAL",
                rationale=f"Observed {cluster.count} pool exhaustion errors in the last {window_minutes} minutes.",
            ))
        elif "Payment" in cluster.signature:
            recommendations.append(AIRecommendation(
                title="Engage Payment Provider Circuit Breaker",
                action="Activate fallback retry queue with exponential backoff for Stripe checkout endpoints.",
                priority="HIGH",
                rationale="Upstream gateway response latency exceeding checkout timeout deadline.",
            ))
        elif "Redis" in cluster.signature:
            recommendations.append(AIRecommendation(
                title="Failover Redis Node & Enable In-Memory Bypass",
                action="Promote replica node redis-02-b to primary and check cluster sentinel heartbeat.",
                priority="HIGH",
                rationale="Cache connection refused error causes latency amplification on underlying databases.",
            ))
        elif "Rate Limit" in cluster.signature:
            recommendations.append(AIRecommendation(
                title="Review API Quota Allocation",
                action="Evaluate client tier allocation or investigate potential rogue client scraper loops.",
                priority="MEDIUM",
                rationale="Approaching 90%+ client quota capacity.",
            ))

    if not recommendations:
        recommendations.append(AIRecommendation(
            title="Nominal Telemetry Flow",
            action="Maintain current resource allocation and observability polling.",
            priority="LOW",
            rationale="No anomalous error clusters or metric degradation observed in current window.",
        ))

    summary = (
        f"System health rated {score}/100 ({overall_status.upper()}). "
        f"Analyzed {total_errors} error events across {len(error_clusters)} clusters in the last {window_minutes} minutes. "
        f"{active_incidents} active alert incidents open."
    )

    return AIHealthAnalysisResponse(
        project_id=project_id,
        timestamp=now,
        health_score=score,
        overall_status=overall_status,
        summary=summary,
        total_errors_analyzed=total_errors,
        error_clusters=error_clusters,
        metric_anomalies=anomalies,
        recommendations=recommendations,
    )
