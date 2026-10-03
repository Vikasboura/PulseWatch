import atexit
import logging
import queue
import threading
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import requests

logger = logging.getLogger("pulsewatch.client")


class PulseWatchClient:
    """
    Lightweight, asynchronous batching client for PulseWatch ingestion.
    Queues telemetry locally and flushes in batches via a background daemon thread.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8000/api/v1",
        batch_size: int = 50,
        flush_interval: float = 2.0,
        timeout: float = 5.0,
    ):
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.batch_size = max(1, min(batch_size, 500))
        self.flush_interval = flush_interval
        self.timeout = timeout

        self._log_queue: queue.Queue = queue.Queue(maxsize=10000)
        self._metric_queue: queue.Queue = queue.Queue(maxsize=10000)
        self._stop_event = threading.Event()

        # Start background worker daemon
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

        # Auto-flush upon application termination
        atexit.register(self.close)

    def send_log(
        self,
        message: str,
        level: str = "INFO",
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ):
        """Enqueue a log record non-blockingly."""
        ts = timestamp or datetime.now(timezone.utc)
        item = {
            "level": level.upper(),
            "message": str(message)[:10000],
            "metadata": metadata or {},
            "timestamp": ts.isoformat(),
        }
        try:
            self._log_queue.put_nowait(item)
        except queue.Full:
            logger.warning("PulseWatch log buffer is full. Dropping log record.")

    def send_metric(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ):
        """Enqueue a time-series metric datapoint non-blockingly."""
        ts = timestamp or datetime.now(timezone.utc)
        item = {
            "name": str(name)[:100],
            "value": float(value),
            "labels": labels or {},
            "timestamp": ts.isoformat(),
        }
        try:
            self._metric_queue.put_nowait(item)
        except queue.Full:
            logger.warning("PulseWatch metric buffer is full. Dropping metric point.")

    def flush(self):
        """Manually flush all currently queued logs and metrics to the PulseWatch server."""
        self._flush_logs()
        self._flush_metrics()

    def close(self):
        """Flush remaining items and terminate the background worker thread."""
        self._stop_event.set()
        try:
            self.flush()
        except Exception:
            pass

    def _flush_logs(self):
        items: List[dict] = []
        while not self._log_queue.empty() and len(items) < self.batch_size:
            try:
                items.append(self._log_queue.get_nowait())
            except queue.Empty:
                break

        if not items:
            return

        url = f"{self.base_url}/ingest/logs"
        headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        try:
            resp = requests.post(url, json={"items": items}, headers=headers, timeout=self.timeout)
            if resp.status_code not in (200, 201, 202):
                logger.warning(f"PulseWatch log ingestion failed ({resp.status_code}): {resp.text}")
        except Exception as e:
            logger.warning(f"PulseWatch failed to send logs batch: {e}")

    def _flush_metrics(self):
        items: List[dict] = []
        while not self._metric_queue.empty() and len(items) < self.batch_size:
            try:
                items.append(self._metric_queue.get_nowait())
            except queue.Empty:
                break

        if not items:
            return

        url = f"{self.base_url}/ingest/metrics"
        headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        try:
            resp = requests.post(url, json={"items": items}, headers=headers, timeout=self.timeout)
            if resp.status_code not in (200, 201, 202):
                logger.warning(f"PulseWatch metric ingestion failed ({resp.status_code}): {resp.text}")
        except Exception as e:
            logger.warning(f"PulseWatch failed to send metrics batch: {e}")

    def _worker_loop(self):
        last_flush = time.time()
        while not self._stop_event.is_set():
            time.sleep(0.2)
            now = time.time()

            has_enough_logs = self._log_queue.qsize() >= self.batch_size
            has_enough_metrics = self._metric_queue.qsize() >= self.batch_size
            is_interval_elapsed = (now - last_flush) >= self.flush_interval

            if has_enough_logs or has_enough_metrics or is_interval_elapsed:
                self._flush_logs()
                self._flush_metrics()
                last_flush = now
