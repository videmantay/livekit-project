import threading
import time
from collections import defaultdict, deque
from functools import lru_cache

from fastapi import HTTPException, Request

from app.config import get_settings


class RateLimiter:
    """Sliding window per client, in memory, so each Cloud Run instance counts separately.

    Keep the service's max-instances low so the effective limit stays meaningful.
    """

    def __init__(self, limit: int, window_seconds: float = 60):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window
        with self._lock:
            # Drop idle clients so memory can't grow without bound.
            for other in [k for k, hits in self._hits.items() if hits[-1] <= cutoff]:
                del self._hits[other]
            hits = self._hits[key]
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True


@lru_cache
def get_limiter() -> RateLimiter:
    return RateLimiter(get_settings().rate_limit_per_minute)


def client_ip(request: Request) -> str:
    # Cloud Run appends the real client address last. Earlier entries are client-supplied.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(request: Request) -> None:
    if not get_limiter().allow(client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many requests")
