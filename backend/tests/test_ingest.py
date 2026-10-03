import pytest
from app.core.rate_limiter import rate_limiter
from app.core.config import settings


@pytest.fixture
def setup_project_and_key(client):
    """Helper fixture to create a user, project, and API key."""
    # Register & Login
    client.post("/api/v1/auth/register", json={
        "email": "ingest_tester@pulsewatch.dev",
        "password": "Password123!",
    })
    token = client.post("/api/v1/auth/login", json={
        "email": "ingest_tester@pulsewatch.dev",
        "password": "Password123!",
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create project
    proj = client.post("/api/v1/projects", headers=headers, json={
        "name": "Ingest Test Project",
        "retention_days": 30,
    }).json()
    project_id = proj["id"]

    # Create API key
    key_data = client.post(f"/api/v1/projects/{project_id}/api-keys", headers=headers, json={
        "name": "Test Key"
    }).json()
    raw_key = key_data["raw_key"]

    # Reset rate limiter
    rate_limiter.reset()

    return {
        "token": token,
        "auth_headers": headers,
        "project_id": project_id,
        "raw_key": raw_key,
        "api_key_headers": {"X-API-Key": raw_key},
    }


def test_ingest_auth_validation(client, setup_project_and_key):
    info = setup_project_and_key

    # 1. No API key provided -> 401
    res = client.post("/api/v1/ingest/logs", json={"level": "INFO", "message": "Test"})
    assert res.status_code == 401

    # 2. Invalid API key provided -> 401
    res_bad = client.post(
        "/api/v1/ingest/logs",
        headers={"X-API-Key": "pw_live_invalidkey123"},
        json={"level": "INFO", "message": "Test"}
    )
    assert res_bad.status_code == 401


def test_ingest_logs_single_and_batch(client, setup_project_and_key):
    info = setup_project_and_key
    headers = info["api_key_headers"]

    # 1. Single log ingestion
    single_res = client.post(
        "/api/v1/ingest/logs",
        headers=headers,
        json={
            "level": "ERROR",
            "message": "Database connection timeout",
            "metadata": {"retry_count": 3, "db_host": "db.prod.internal"}
        }
    )
    assert single_res.status_code == 202
    assert single_res.json()["ingested"] == 1

    # 2. Batch log ingestion
    batch_items = [
        {"level": "INFO", "message": f"User logged in #{i}", "metadata": {"user_id": f"usr_{i}"}}
        for i in range(10)
    ]
    batch_res = client.post(
        "/api/v1/ingest/logs",
        headers=headers,
        json={"items": batch_items}
    )
    assert batch_res.status_code == 202
    assert batch_res.json()["ingested"] == 10


def test_ingest_log_caps_and_validation(client, setup_project_and_key):
    info = setup_project_and_key
    headers = info["api_key_headers"]

    # 1. Batch size exceeding cap (> 500)
    oversized_batch = [
        {"level": "INFO", "message": f"Log #{i}"}
        for i in range(settings.MAX_INGEST_BATCH_SIZE + 1)
    ]
    res_over = client.post(
        "/api/v1/ingest/logs",
        headers=headers,
        json={"items": oversized_batch}
    )
    assert res_over.status_code == 422 or res_over.status_code == 400

    # 2. Message length exceeding cap (> 10000 chars)
    giant_message = "A" * (settings.MAX_LOG_MESSAGE_LENGTH + 10)
    res_len = client.post(
        "/api/v1/ingest/logs",
        headers=headers,
        json={"level": "INFO", "message": giant_message}
    )
    assert res_len.status_code == 422


def test_ingest_metrics_single_and_batch(client, setup_project_and_key):
    info = setup_project_and_key
    headers = info["api_key_headers"]

    # 1. Single metric
    single_res = client.post(
        "/api/v1/ingest/metrics",
        headers=headers,
        json={
            "name": "cpu_utilization",
            "value": 78.4,
            "labels": {"instance": "worker-1"}
        }
    )
    assert single_res.status_code == 202
    assert single_res.json()["ingested"] == 1

    # 2. Batch metrics
    batch_metrics = [
        {"name": "http_latency_ms", "value": 45.2 + i, "labels": {"endpoint": "/api/users"}}
        for i in range(5)
    ]
    batch_res = client.post(
        "/api/v1/ingest/metrics",
        headers=headers,
        json={"items": batch_metrics}
    )
    assert batch_res.status_code == 202
    assert batch_res.json()["ingested"] == 5


def test_ingest_rate_limiting(client, setup_project_and_key):
    info = setup_project_and_key
    headers = info["api_key_headers"]

    # Configure a temporary tight rate limit for testing
    original_limit = settings.RATE_LIMIT_PER_MINUTE
    settings.RATE_LIMIT_PER_MINUTE = 5
    try:
        # First 5 requests should succeed
        for i in range(5):
            res = client.post(
                "/api/v1/ingest/logs",
                headers=headers,
                json={"level": "INFO", "message": f"Message {i}"}
            )
            assert res.status_code == 202

        # 6th request should be rejected with 429
        res_blocked = client.post(
            "/api/v1/ingest/logs",
            headers=headers,
            json={"level": "INFO", "message": "Should be rate limited"}
        )
        assert res_blocked.status_code == 429
        assert "Rate limit exceeded" in res_blocked.json()["detail"]
    finally:
        settings.RATE_LIMIT_PER_MINUTE = original_limit
        rate_limiter.reset()
