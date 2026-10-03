"""
PulseWatch Locust Ingestion Load Test
--------------------------------------
Measures log and metric ingestion throughput (req/s) and latency distribution (p50, p95, p99).

Run interactively with Web UI:
    locust -f locustfile.py --host http://localhost:8000

Run headless (CLI):
    locust -f locustfile.py --host http://localhost:8000 --headless -u 50 -r 10 --run-time 1m --csv=results
"""

import os
import random
from locust import HttpUser, task, between, events


class PulseWatchIngestUser(HttpUser):
    # Short wait time to simulate high-throughput client buffering
    wait_time = between(0.01, 0.05)

    def on_start(self):
        """Prepare authentication headers for ingestion."""
        self.api_key = os.getenv("PULSEWATCH_API_KEY", "")
        
        # If no key is provided via env, attempt automated test registration
        if not self.api_key:
            try:
                # Register test user
                test_email = f"loadtest_{random.randint(1000, 99999)}@pulsewatch.test"
                reg_resp = self.client.post("/api/v1/auth/register", json={
                    "email": test_email,
                    "password": "LoadTestPassword123!",
                    "full_name": "Load Tester"
                })
                # Login
                login_resp = self.client.post("/api/v1/auth/login", json={
                    "email": test_email,
                    "password": "LoadTestPassword123!"
                })
                token = login_resp.json().get("access_token")
                auth_headers = {"Authorization": f"Bearer {token}"}
                
                # Create project
                proj_resp = self.client.post("/api/v1/projects", headers=auth_headers, json={
                    "name": "Load Test Target Project",
                    "retention_days": 7
                })
                project_id = proj_resp.json().get("id")
                
                # Create API key
                key_resp = self.client.post(f"/api/v1/projects/{project_id}/api-keys", headers=auth_headers, json={
                    "name": "Locust Load Key"
                })
                self.api_key = key_resp.json().get("raw_key")
            except Exception as e:
                print(f"Warning: Could not auto-generate API key: {e}")
                self.api_key = "pw_live_fallback_loadtest_key"

        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

    @task(5)
    def ingest_single_log(self):
        """Task: Ingest a single log event."""
        payload = {
            "level": random.choice(["INFO", "DEBUG", "WARNING"]),
            "message": f"User action completed in {random.randint(20, 200)}ms",
            "metadata": {"endpoint": "/api/v1/checkout", "user_id": f"u_{random.randint(1, 1000)}"}
        }
        self.client.post("/api/v1/ingest/logs", json=payload, headers=self.headers, name="/ingest/logs [single]")

    @task(3)
    def ingest_batch_logs(self):
        """Task: Ingest a batch of 25 logs."""
        batch = [
            {
                "level": "INFO" if i % 10 != 0 else "ERROR",
                "message": f"Batch transaction event #{i}",
                "metadata": {"item_idx": i, "batch_id": "b_100"}
            }
            for i in range(25)
        ]
        self.client.post("/api/v1/ingest/logs", json={"items": batch}, headers=self.headers, name="/ingest/logs [batch-25]")

    @task(4)
    def ingest_batch_metrics(self):
        """Task: Ingest a batch of 10 time-series metrics."""
        metrics = [
            {
                "name": random.choice(["cpu_load", "response_time_ms", "memory_usage_mb"]),
                "value": round(random.uniform(10.0, 500.0), 2),
                "labels": {"cluster": "node-1", "env": "prod"}
            }
            for _ in range(10)
        ]
        self.client.post("/api/v1/ingest/metrics", json={"items": metrics}, headers=self.headers, name="/ingest/metrics [batch-10]")
