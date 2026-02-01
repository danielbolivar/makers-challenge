"""
Per-user (and optional per-channel) rate limiting.
Sliding window in-memory; applied in adapter before calling the agent.
"""

import time
from collections import defaultdict
from threading import Lock

from src.config import settings


def _key(user_id: str, channel_id: str | None) -> str:
    if channel_id is None:
        return user_id
    return f"{user_id}:{channel_id}"


class RateLimiter:
    """
    In-memory sliding-window rate limiter.
    Max RATE_LIMIT_REQUESTS per RATE_LIMIT_WINDOW_SECONDS per key (user_id or user_id:channel_id).
    """

    def __init__(
        self,
        max_requests: int | None = None,
        window_seconds: int | None = None,
    ):
        self.max_requests = max_requests or settings.RATE_LIMIT_REQUESTS
        self.window_seconds = window_seconds or settings.RATE_LIMIT_WINDOW_SECONDS
        self._timestamps: defaultdict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def _prune(self, key: str, now: float) -> None:
        cutoff = now - self.window_seconds
        self._timestamps[key] = [t for t in self._timestamps[key] if t > cutoff]

    def check_and_record(self, user_id: str, channel_id: str | None = None) -> bool:
        """
        If under limit: record the request and return True.
        If at or over limit: do not record, return False.
        """
        key = _key(user_id, channel_id)
        now = time.monotonic()
        with self._lock:
            self._prune(key, now)
            if len(self._timestamps[key]) >= self.max_requests:
                return False
            self._timestamps[key].append(now)
            return True

    def check_only(self, user_id: str, channel_id: str | None = None) -> bool:
        """Return True if a request would be allowed (without recording)."""
        key = _key(user_id, channel_id)
        now = time.monotonic()
        with self._lock:
            self._prune(key, now)
            return len(self._timestamps[key]) < self.max_requests


_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
