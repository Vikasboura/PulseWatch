"""
PulseWatch In-Memory Rate Limiter
----------------------------------
Provides sliding-window rate limiting per API key.

SINGLE-INSTANCE NOTICE:
This in-memory implementation maintains timestamps inside the running Python process.
It is lightweight and zero-dependency, ideal for single-instance hosts (e.g., Render/Railway,
single Cloud Run instance, VPS).
For multi-instance horizontal scaling, swap this out or configure a Redis-backed
sliding window (using Redis sorted sets `ZREMRANGEBYSCORE` and `ZCARD`).
"""

import time
from collections import defaultdict
from threading import Lock
from typing import Tuple


class InMemoryRateLimiter:
    def __init__(self):
        # Maps key_id -> list of float timestamps (epoch seconds)
        self._history: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, key_id: str, limit: int, window_seconds: int = 60) -> Tuple[bool, int, int]:
        """
        Check if request for key_id is allowed under sliding window.
        Returns:
            (is_allowed: bool, current_usage: int, remaining: int)
        """
        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            timestamps = self._history[key_id]
            # Prune timestamps older than window_start
            valid_timestamps = [t for t in timestamps if t > window_start]
            
            if len(valid_timestamps) >= limit:
                self._history[key_id] = valid_timestamps
                return False, len(valid_timestamps), 0

            # Record this request
            valid_timestamps.append(now)
            self._history[key_id] = valid_timestamps
            remaining = limit - len(valid_timestamps)
            return True, len(valid_timestamps), remaining

    def reset(self, key_id: str = None):
        """Reset history (useful in tests)."""
        with self._lock:
            if key_id:
                self._history.pop(key_id, None)
            else:
                self._history.clear()


rate_limiter = InMemoryRateLimiter()
