"""
PulseWatch Ingestion Load & Performance Benchmark
---------------------------------------------------
Measures throughput (requests/sec), p50, p90, p95, p99 latency distributions,
and error rates under concurrent load against the PulseWatch API.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
import httpx
import math


BASE_URL = os.getenv("PULSEWATCH_URL", "http://localhost:8001/api/v1")
API_KEY = os.getenv("PULSEWATCH_API_KEY", "pw_live_demo")
TOTAL_REQUESTS = 1000
CONCURRENCY = 25


async def send_log_batch(client: httpx.AsyncClient, batch_id: int) -> float:
    url = f"{BASE_URL}/ingest/logs"
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    payload = {
        "items": [
            {
                "level": "INFO" if i % 10 != 0 else "ERROR",
                "message": f"Benchmark synthetic event {batch_id}-{i} completed in 42ms",
                "metadata": {"batch": batch_id, "worker_idx": i, "env": "loadtest"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            for i in range(10)
        ]
    }
    start = time.perf_counter()
    resp = await client.post(url, json=payload, headers=headers, timeout=10.0)
    duration_ms = (time.perf_counter() - start) * 1000.0
    if resp.status_code not in (200, 201, 202):
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
    return duration_ms


async def send_metric_batch(client: httpx.AsyncClient, batch_id: int) -> float:
    url = f"{BASE_URL}/ingest/metrics"
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    payload = {
        "items": [
            {
                "name": "benchmark_throughput_qps",
                "value": round(float(batch_id * 1.5), 2),
                "labels": {"source": "loadtest", "run": "p95_eval"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            for _ in range(5)
        ]
    }
    start = time.perf_counter()
    resp = await client.post(url, json=payload, headers=headers, timeout=10.0)
    duration_ms = (time.perf_counter() - start) * 1000.0
    if resp.status_code not in (200, 201, 202):
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
    return duration_ms


async def worker(
    queue: asyncio.Queue,
    client: httpx.AsyncClient,
    latencies: list,
    errors: list,
):
    while True:
        try:
            req_type, idx = queue.get_nowait()
        except asyncio.QueueEmpty:
            break

        try:
            if req_type == "log":
                lat = await send_log_batch(client, idx)
            else:
                lat = await send_metric_batch(client, idx)
            latencies.append(lat)
        except Exception as e:
            errors.append(str(e))
        finally:
            queue.task_done()


async def run_benchmark():
    print(f"==================================================")
    print(f"[*] PulseWatch Ingestion Performance Benchmark")
    print(f"Target:      {BASE_URL}")
    print(f"Concurrency: {CONCURRENCY} workers")
    print(f"Total Reqs:  {TOTAL_REQUESTS}")
    print(f"==================================================")

    queue = asyncio.Queue()
    for i in range(TOTAL_REQUESTS):
        # 60% logs, 40% metrics
        req_type = "log" if i % 10 < 6 else "metric"
        queue.put_nowait((req_type, i))

    latencies = []
    errors = []

    limits = httpx.Limits(max_keepalive_connections=CONCURRENCY, max_connections=CONCURRENCY * 2)
    async with httpx.AsyncClient(limits=limits) as client:
        start_time = time.perf_counter()
        tasks = [
            asyncio.create_task(worker(queue, client, latencies, errors))
            for _ in range(CONCURRENCY)
        ]
        await asyncio.gather(*tasks)
        total_duration = time.perf_counter() - start_time

    total_success = len(latencies)
    total_errors = len(errors)
    rps = total_success / total_duration if total_duration > 0 else 0

    def get_percentile(sorted_list: list, pct: float) -> float:
        if not sorted_list:
            return 0.0
        k = (len(sorted_list) - 1) * (pct / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_list[int(k)]
        d0 = sorted_list[int(f)] * (c - k)
        d1 = sorted_list[int(c)] * (k - f)
        return d0 + d1

    sorted_lats = sorted(latencies) if latencies else []
    p50 = get_percentile(sorted_lats, 50)
    p90 = get_percentile(sorted_lats, 90)
    p95 = get_percentile(sorted_lats, 95)
    p99 = get_percentile(sorted_lats, 99)
    mean_lat = sum(latencies) / len(latencies) if latencies else 0.0
    min_lat = sorted_lats[0] if sorted_lats else 0.0
    max_lat = sorted_lats[-1] if sorted_lats else 0.0

    # Total telemetry items ingested (avg 8 items per request)
    total_items = sum(10 if i % 10 < 6 else 5 for i in range(total_success))

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "target_url": BASE_URL,
        "concurrency": CONCURRENCY,
        "total_requests": TOTAL_REQUESTS,
        "successful_requests": total_success,
        "failed_requests": total_errors,
        "total_duration_seconds": round(total_duration, 3),
        "requests_per_second": round(rps, 2),
        "telemetry_events_ingested": total_items,
        "telemetry_events_per_second": round(total_items / total_duration, 2),
        "latency_ms": {
            "min": round(min_lat, 2),
            "mean": round(mean_lat, 2),
            "p50": round(p50, 2),
            "p90": round(p90, 2),
            "p95": round(p95, 2),
            "p99": round(p99, 2),
            "max": round(max_lat, 2),
        },
    }

    print("\n[+] Benchmark Results Summary:")
    print(f"--------------------------------------------------")
    print(f"Throughput:     {results['requests_per_second']:,} req/sec")
    print(f"Event Rate:     {results['telemetry_events_per_second']:,} events/sec")
    print(f"Total Duration: {results['total_duration_seconds']}s")
    print(f"Success / Err:  {total_success} / {total_errors} ({round(total_errors / TOTAL_REQUESTS * 100, 2)}% error)")
    print(f"p50 Latency:    {results['latency_ms']['p50']} ms")
    print(f"p90 Latency:    {results['latency_ms']['p90']} ms")
    print(f"p95 Latency:    {results['latency_ms']['p95']} ms [Target SLA]")
    print(f"p99 Latency:    {results['latency_ms']['p99']} ms")
    print(f"Mean Latency:   {results['latency_ms']['mean']} ms")
    print(f"--------------------------------------------------")

    # Save to JSON
    output_path = os.path.join(os.path.dirname(__file__), "benchmark_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Saved benchmark numbers to {output_path}")

    return results


if __name__ == "__main__":
    asyncio.run(run_benchmark())
