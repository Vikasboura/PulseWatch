from datetime import datetime, timezone
import pytest
from app.models.log_record import LogRecord
from app.models.metric_record import MetricRecord


@pytest.fixture
def setup_ai_project(client, db_session):
    client.post("/api/v1/auth/register", json={
        "email": "ai_tester@pulsewatch.dev",
        "password": "Password123!",
    })
    token = client.post("/api/v1/auth/login", json={
        "email": "ai_tester@pulsewatch.dev",
        "password": "Password123!",
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    proj = client.post("/api/v1/projects", headers=headers, json={
        "name": "AI Test Project",
        "retention_days": 7,
    }).json()
    
    return {"headers": headers, "project_id": proj["id"]}


def test_ai_insights_auth_required(client, setup_ai_project):
    pid = setup_ai_project["project_id"]
    resp = client.get(f"/api/v1/projects/{pid}/ai/insights")
    assert resp.status_code == 401


def test_ai_insights_health_analysis(client, setup_ai_project, db_session):
    headers = setup_ai_project["headers"]
    project_id = setup_ai_project["project_id"]
    now = datetime.now(timezone.utc)
    
    # Ingest synthetic error logs with distinct failure signatures
    db_session.add_all([
        LogRecord(
            project_id=project_id,
            timestamp=now,
            level="ERROR",
            message="DatabaseConnectionError: Postgres pool exhausted (active=20, max=20)",
        ),
        LogRecord(
            project_id=project_id,
            timestamp=now,
            level="ERROR",
            message="PaymentGatewayTimeout: upstream 504 Gateway Timeout from Stripe",
        ),
        LogRecord(
            project_id=project_id,
            timestamp=now,
            level="ERROR",
            message="RedisConnectionRefused: Cache cluster node redis-02 unreachable",
        ),
        LogRecord(
            project_id=project_id,
            timestamp=now,
            level="WARNING",
            message="RateLimitWarning: Client approaching quota (92/100 requests)",
        ),
        MetricRecord(
            project_id=project_id,
            timestamp=now,
            name="http_latency_ms",
            value=310.0,
        )
    ])
    db_session.commit()

    resp = client.get(f"/api/v1/projects/{project_id}/ai/insights?window_minutes=60", headers=headers)
    assert resp.status_code == 200
    
    # Verify API platform headers
    assert "x-request-id" in resp.headers
    assert "x-ratelimit-limit" in resp.headers
    assert "x-ratelimit-remaining" in resp.headers

    data = resp.json()
    assert data["project_id"] == project_id
    assert data["total_errors_analyzed"] >= 4
    assert len(data["error_clusters"]) >= 3
    assert len(data["recommendations"]) >= 1

    # Verify cluster signatures
    signatures = [c["signature"] for c in data["error_clusters"]]
    assert any("Connection Pool" in s for s in signatures)
    assert any("Payment" in s for s in signatures)
    assert any("Redis" in s for s in signatures)

    # Verify on-demand trigger endpoint
    post_resp = client.post(f"/api/v1/projects/{project_id}/ai/analyze?window_minutes=60", headers=headers)
    assert post_resp.status_code == 200
    assert post_resp.json()["total_errors_analyzed"] >= 4
