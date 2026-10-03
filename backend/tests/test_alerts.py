import json
from datetime import datetime, timezone, timedelta
import pytest
from starlette.websockets import WebSocketDisconnect

from app.models.log_record import LogRecord
from app.models.metric_record import MetricRecord
from app.models.alert import AlertRule, AlertEvent
from app.services.alert_evaluator import evaluate_single_rule


@pytest.fixture
def alert_setup(client, db_session):
    # Register & Login
    client.post("/api/v1/auth/register", json={
        "email": "alert_mgr@pulsewatch.dev",
        "password": "Password123!",
    })
    token = client.post("/api/v1/auth/login", json={
        "email": "alert_mgr@pulsewatch.dev",
        "password": "Password123!",
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create project
    proj = client.post("/api/v1/projects", headers=headers, json={
        "name": "Alerts Test Project",
        "retention_days": 30,
    }).json()
    project_id = proj["id"]

    # Create API key
    key_data = client.post(f"/api/v1/projects/{project_id}/api-keys", headers=headers, json={
        "name": "Alert Key"
    }).json()
    raw_key = key_data["raw_key"]
    ingest_headers = {"X-API-Key": raw_key}

    return {
        "token": token,
        "headers": headers,
        "project_id": project_id,
        "raw_key": raw_key,
        "ingest_headers": ingest_headers,
    }


def test_alert_rule_crud(client, alert_setup):
    info = alert_setup
    headers = info["headers"]
    project_id = info["project_id"]

    # 1. Create error_count rule
    create_res = client.post(
        f"/api/v1/projects/{project_id}/alerts/rules",
        headers=headers,
        json={
            "name": "High Error Spike",
            "rule_type": "error_count",
            "condition_operator": ">",
            "threshold": 5.0,
            "window_minutes": 5,
            "channel_type": "slack",
            "channel_config": {"webhook_url": "https://hooks.slack.com/services/mock"},
            "notification_cooldown_minutes": 10,
        },
    )
    assert create_res.status_code == 201
    rule_data = create_res.json()
    rule_id = rule_data["id"]
    assert rule_data["threshold"] == 5.0
    assert rule_data["channel_type"] == "slack"

    # 2. List rules
    list_res = client.get(f"/api/v1/projects/{project_id}/alerts/rules", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # 3. Update rule
    update_res = client.put(
        f"/api/v1/projects/{project_id}/alerts/rules/{rule_id}",
        headers=headers,
        json={"threshold": 10.0, "name": "Critical Error Spike"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["threshold"] == 10.0
    assert update_res.json()["name"] == "Critical Error Spike"

    # 4. Delete rule
    del_res = client.delete(f"/api/v1/projects/{project_id}/alerts/rules/{rule_id}", headers=headers)
    assert del_res.status_code == 204

    # Verify empty
    assert len(client.get(f"/api/v1/projects/{project_id}/alerts/rules", headers=headers).json()) == 0


def test_alert_evaluation_dedup_and_autoresolve(client, alert_setup, db_session):
    info = alert_setup
    headers = info["headers"]
    project_id = info["project_id"]
    ingest_headers = info["ingest_headers"]

    # 1. Create rule: trigger if error count > 3 in last 5 minutes
    rule_res = client.post(
        f"/api/v1/projects/{project_id}/alerts/rules",
        headers=headers,
        json={
            "name": "Error Surge",
            "rule_type": "error_count",
            "condition_operator": ">",
            "threshold": 3.0,
            "window_minutes": 5,
            "channel_type": "email",
            "channel_config": {"email": "ops@pulsewatch.dev"},
            "notification_cooldown_minutes": 15,
        },
    )
    rule_id = rule_res.json()["id"]

    # Query rule from DB
    rule = db_session.query(AlertRule).filter(AlertRule.id == rule_id).first()

    # Ingest 2 errors (below threshold of 3)
    client.post(
        "/api/v1/ingest/logs",
        headers=ingest_headers,
        json={"items": [
            {"level": "ERROR", "message": "Error 1"},
            {"level": "ERROR", "message": "Error 2"},
        ]},
    )

    t1 = datetime.now(timezone.utc) + timedelta(seconds=1)
    ev1 = evaluate_single_rule(rule, db_session, t1)
    assert ev1 is None  # Not breached

    # Ingest 3 more errors -> total 5 errors in window (> 3 threshold)
    client.post(
        "/api/v1/ingest/logs",
        headers=ingest_headers,
        json={"items": [
            {"level": "ERROR", "message": "Error 3"},
            {"level": "ERROR", "message": "Error 4"},
            {"level": "ERROR", "message": "Error 5"},
        ]},
    )

    t2 = datetime.now(timezone.utc) + timedelta(seconds=1)
    # First breached evaluation: Should create 1 AlertEvent
    ev2 = evaluate_single_rule(rule, db_session, t2)
    assert ev2 is not None
    assert ev2.status == "triggered"
    assert ev2.triggered_value == 5.0
    event_id = ev2.id

    # Verify event count in DB
    events = db_session.query(AlertEvent).filter(AlertEvent.rule_id == rule_id).all()
    assert len(events) == 1

    # DEDUPLICATION CHECK: Second evaluation while error count is still 5
    ev3 = evaluate_single_rule(rule, db_session, t2 + timedelta(seconds=10))
    assert ev3 is not None
    assert ev3.id == event_id  # Returns the SAME open event
    # Ensure NO duplicate event was inserted into DB
    events_after = db_session.query(AlertEvent).filter(AlertEvent.rule_id == rule_id).all()
    assert len(events_after) == 1

    # AUTO-RESOLUTION CHECK:
    # Advance time beyond 5-minute window so errors fall out of the rolling window
    future_time = t2 + timedelta(minutes=6)
    ev4 = evaluate_single_rule(rule, db_session, future_time)
    assert ev4 is not None
    assert ev4.status == "resolved"
    assert ev4.resolved_at is not None

    # Query events list via API
    api_events = client.get(f"/api/v1/projects/{project_id}/alerts/events", headers=headers).json()
    assert len(api_events) == 1
    assert api_events[0]["status"] == "resolved"


def test_websocket_auth_and_streaming(client, alert_setup):
    info = alert_setup
    token = info["token"]
    project_id = info["project_id"]

    # 1. Connect without token -> Should close with WS policy violation
    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/live/{project_id}") as ws:
            pass

    # 2. Connect with invalid token -> Should fail
    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/live/{project_id}?token=invalid.token") as ws:
            pass

    # 3. Connect with valid token to own project -> Success!
    with client.websocket_connect(f"/ws/live/{project_id}?token={token}") as websocket:
        # First message should be connected ack
        welcome = websocket.receive_json()
        assert welcome["type"] == "connected"
        assert welcome["project_id"] == project_id

        # Send ping, expect pong
        websocket.send_text("ping")
        pong = websocket.receive_json()
        assert pong["type"] == "pong"
