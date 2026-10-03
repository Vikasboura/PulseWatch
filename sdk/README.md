# PulseWatch Python Client SDK

A lightweight, asynchronous telemetry client for ingesting logs and custom time-series metrics into PulseWatch.

## Features
- **Zero Blocking**: Enqueues logs and metrics in an in-memory queue. Requests are dispatched in batches by a background daemon thread.
- **Native Logging Handler**: Plugs directly into standard Python `logging`.
- **Automatic Metadata Capture**: Contextual extras and exception tracebacks are parsed automatically into structured JSON.
- **Graceful Termination**: Auto-flushes any buffered records upon application shutdown via `atexit`.

---

## Installation

```bash
# From local directory:
pip install -e ./sdk

# Or directly:
pip install ./sdk
```

---

## Quickstart

### 1. Ingesting Logs via Standard Logging

```python
import logging
from pulsewatch import PulseWatchClient, PulseWatchHandler

# Initialize client with your project API key
client = PulseWatchClient(
    api_key="pw_live_YOUR_API_KEY",
    base_url="http://localhost:8000/api/v1",
)

# Attach handler to root logger
logger = logging.getLogger("my_app")
logger.setLevel(logging.INFO)
logger.addHandler(PulseWatchHandler(client))

# Standard logging calls are buffered and ingested
logger.info("Order processed successfully", extra={"order_id": "ord_8819", "total_usd": 49.99})

try:
    1 / 0
except ZeroDivisionError:
    logger.exception("Unexpected calculation failure")
```

### 2. Sending Custom Metrics

```python
from pulsewatch import PulseWatchClient

client = PulseWatchClient(api_key="pw_live_YOUR_API_KEY")

# Send gauge / latency metrics
client.send_metric(
    name="checkout_duration_ms",
    value=214.5,
    labels={"payment_gateway": "stripe", "region": "us-east"}
)

# Explicit manual flush (optional - worker automatically flushes every 2s)
client.flush()
```
