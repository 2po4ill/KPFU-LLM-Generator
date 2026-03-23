"""
In-process rate limiter for production hardening.

Note: this is intentionally simple (memory only) and protects a single
process deployment. For multi-worker production, prefer Redis-backed limits.
"""

import time
import asyncio
from typing import Dict, Tuple


class InMemoryRateLimiter:
    def __init__(self):
        self._lock = asyncio.Lock()
        # key -> (count, reset_timestamp)
        self._state: Dict[str, Tuple[int, float]] = {}

    async def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.time()
        async with self._lock:
            count, reset_ts = self._state.get(key, (0, now + window_seconds))

            # New window
            if now >= reset_ts:
                count = 0
                reset_ts = now + window_seconds

            if count >= limit:
                return False

            self._state[key] = (count + 1, reset_ts)
            return True


rate_limiter = InMemoryRateLimiter()

