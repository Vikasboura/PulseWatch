from datetime import datetime, timezone, timedelta
import pytest
from app.models.log_record import LogRecord
from app.models.metric_record import MetricRecord


@pytest.fixture
def setup_dataset(client, db_session):
    # Register & Login
    client.post("/api/v1/auth/register", json={
        "email": "query_analyst@pulsewatch.dev",
        "password": "Password123!",
    })
    token = client.post("/api/v1/auth/login", json={
        "email": "query_analyst@pulsewatch.dev",
        "password": "Password123!",
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create project with 10 days retention
    proj = client.post("/api/v1/projects", headers=headers, json={
        "name": "Query Test Project",
        "retention_days": 10,
    }).json()
    project_id = proj["id"]

    # Create API key
    key_data = client.post(f"/api/v1/projects/{project_id}/api-keys", headers=headers, json={
        "name": "Query Key"
    }).json()
    raw_key = key_data["raw_key"]
    ingest_headers = {"X-API-Key": raw_key}

    # Ingest diverse logs
    logs = [
        {"level": "INFO", "message": "User authenticated successfully", "metadata": {"ip": "1.2.3.4"}},
        {"level": "WARNING", "message": "High memory consumption detected", "metadata": {"mem_pct": 82}},
        {"level": "ERROR", "message": "Database query timeout after 5000ms", "metadata": {"query_id": "q123"}},
        {"level": "ERROR", "message": "Failed to connect to redis cache", "metadata": {"host": "redis-01"}},
        {"level": "DEBUG", "message": "Cache miss for key user:101", "metadata": {}},
    ]
    client.post("/api/v1/ingest/logs", headers=ingest_headers, json={"items": logs})

    # Ingest metrics
    now = datetime.now(timezone.utc)
    metrics = [
        {"name": "response_time_ms", "value": 120.0, "timestamp": (now - timedelta(minutes=4)).isoformat()},
        {"name": "response_time_ms", "value": 180.0, "timestamp": (now - timedelta(minutes=3)).isoformat()},
        {"name": "response_time_ms", "value": 240.0, "timestamp": (now - timedelta(minutes=2)).isoformat()},
        {"name": "response_time_ms", "value": 300.0, "timestamp": (now - timedelta(minutes=1)).isoformat()},
        {"name": "cpu_load", "value": 45.0, "timestamp": now.isoformat()},
    ]
    client.post("/api/v1/ingest/metrics", headers=ingest_headers, json={"items": metrics})

    return {
        "headers": headers,
        "project_id": project_id,
        "ingest_headers": ingest_headers,
    }


def test_query_logs_filters_and_search(client, setup_dataset):
    info = setup_dataset
    headers = info["headers"]
    project_id = info["project_id"]

    # 1. Query all logs
    res_all = client.get(f"/api/v1/projects/{project_id}/logs", headers=headers)
    assert res_all.status_code == 200
    data_all = res_all.json()
    assert data_all["total"] == 5
    assert len(data_all["items"]) == 5

    # 2. Filter by level ERROR
    res_err = client.get(f"/api/v1/projects/{project_id}/logs?level=ERROR", headers=headers)
    assert res_err.status_code == 200
    data_err = res_err.json()
    assert data_err["total"] == 2
    for item in data_err["items"]:
        assert item["level"] == "ERROR"

    # 3. Substring search for "timeout"
    res_search = client.get(f"/api/v1/projects/{project_id}/logs?search=timeout", headers=headers)
    assert res_search.status_code == 200
    data_search = res_search.json()
    assert data_search["total"] == 1
    assert "Database query timeout" in data_search["items"][0]["message"]
    assert data_search["items"][0]["metadata"]["query_id"] == "q123"

    # 4. Pagination (limit=2, page=1 and page=2)
    p1 = client.get(f"/api/v1/projects/{project_id}/logs?limit=2&page=1", headers=headers).json()
    assert len(p1["items"]) == 2
    assert p1["has_more"] is True

    p2 = client.get(f"/api/v1/projects/{project_id}/logs?limit=2&page=2", headers=headers).json()
    assert len(p2["items"]) == 2
    assert p2["has_more"] is True


def test_query_metrics_and_bucketing(client, setup_dataset):
    info = setup_dataset
    headers = info["headers"]
    project_id = info["project_id"]

    # 1. Get metric names
    names_res = client.get(f"/api/v1/projects/{project_id}/metrics/names", headers=headers)
    assert names_res.status_code == 200
    names = [n["name"] for n in names_res.json()]
    assert "response_time_ms" in names
    assert "cpu_load" in names

    # 2. Query aggregated metrics (5m bucket)
    metric_res = client.get(
        f"/api/v1/projects/{project_id}/metrics?name=response_time_ms&bucket=5m",
        headers=headers,
    )
    assert metric_res.status_code == 200
    metric_data = metric_res.json()
    assert metric_data["metric_name"] == "response_time_ms"
    assert len(metric_data["points"]) >= 1

    # Verify min, max, avg
    first_bucket = metric_data["points"][0]
    assert first_bucket["min"] <= first_bucket["max"]
    assert first_bucket["avg"] >= first_bucket["min"]
    assert first_bucket["count"] >= 1


def test_data_retention_purge(client, setup_dataset, db_session):
    info = setup_dataset
    headers = info["headers"]
    project_id = info["project_id"]

    # Insert an old log and old metric manually (e.g. 20 days old, while retention is 10 days)
    old_time = datetime.now(timezone.utc) - timedelta(days=20)
    old_log = LogRecord(
        project_id=project_id,
        level="INFO",
        message="Ancient log from 20 days ago",
        log_metadata={},
        timestamp=old_time,
    )
    old_metric = MetricRecord(
        project_id=project_id,
        name="ancient_metric",
        value=1.0,
        timestamp=old_time,
        labels={},
    )
    db_session.add(old_log)
    db_session.add(old_metric)
    db_session.commit()

    # Verify old records exist
    assert db_session.query(LogRecord).filter(LogRecord.project_id == project_id).count() == 6
    assert db_session.query(MetricRecord).filter(MetricRecord.project_id == project_id).count() == 6

    # Trigger retention purge endpoint
    purge_res = client.post(f"/api/v1/projects/{project_id}/retention/purge", headers=headers)
    assert purge_res.status_code == 200
    data = purge_res.json()
    assert data["logs_purged"] == 1
    assert data["metrics_purged"] == 1

    # Verify that the ancient records are gone, while recent 5 logs and 5 metrics remain
    assert db_session.query(LogRecord).filter(LogRecord.project_id == project_id).count() == 5
    assert db_session.query(MetricRecord).filter(MetricRecord.project_id == project_id).count() == 5
