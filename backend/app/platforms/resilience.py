import logging
import os
import time
from typing import List, Optional

import redis

from app.core.config import settings
from app.core.errors import AppError

logger = logging.getLogger("anystream.resilience")

# Redis connection
redis_client: Optional[redis.Redis] = None
try:
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception:
    pass


class PlatformCircuitBreakerError(AppError):
    def __init__(self, platform_id: str, retry_after: int = 30):
        super().__init__(
            status_code=503,
            error_code="PLATFORM_CIRCUIT_OPEN",
            message=f"Platform '{platform_id}' is temporarily experiencing high upstream failure rates. Please try again in {retry_after}s.",
            details={"platform_id": platform_id, "retry_after": retry_after},
        )


class PlatformCircuitBreaker:
    """
    Redis-backed circuit breaker protecting against cascading upstream outages.
    - If a platform fails >= failure_threshold times within time_window, opens circuit.
    - Stays open for cooldown_seconds before half-open probe.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        cooldown_seconds: int = 30,
        time_window: int = 60,
    ):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.time_window = time_window

    def is_available(self, platform_id: str) -> bool:
        if not redis_client or not platform_id:
            return True

        open_key = f"circuit:{platform_id}:open"
        try:
            if redis_client.get(open_key):
                return False
            return True
        except Exception:
            return True

    def record_failure(self, platform_id: str) -> None:
        if not redis_client or not platform_id:
            return

        fail_key = f"circuit:{platform_id}:failures"
        open_key = f"circuit:{platform_id}:open"

        try:
            fails = redis_client.incr(fail_key)
            if fails == 1:
                redis_client.expire(fail_key, self.time_window)

            if fails >= self.failure_threshold:
                logger.warning("Circuit breaker OPENED for platform [%s] after %d failures.", platform_id, fails)
                redis_client.setex(open_key, self.cooldown_seconds, "open")
                redis_client.delete(fail_key)
        except Exception as e:
            logger.debug("Circuit breaker failure recording error: %s", str(e))

    def record_success(self, platform_id: str) -> None:
        if not redis_client or not platform_id:
            return

        fail_key = f"circuit:{platform_id}:failures"
        open_key = f"circuit:{platform_id}:open"

        try:
            redis_client.delete(fail_key)
            redis_client.delete(open_key)
        except Exception:
            pass


class ProxyManager:
    """
    Manages rotation and health scoring across configured egress HTTP/SOCKS5 proxies.
    Configured via EGRESS_PROXIES env var (comma-separated URLs).
    """

    def __init__(self, proxy_list: Optional[List[str]] = None):
        raw = os.getenv("EGRESS_PROXIES", "")
        self.proxies: List[str] = proxy_list or ([p.strip() for p in raw.split(",") if p.strip()] if raw else [])
        self._index = 0

    def get_proxy(self) -> Optional[str]:
        if not self.proxies:
            return None
        proxy = self.proxies[self._index % len(self.proxies)]
        self._index += 1
        return proxy

    def has_proxies(self) -> bool:
        return len(self.proxies) > 0


# Default instances
circuit_breaker = PlatformCircuitBreaker()
proxy_manager = ProxyManager()

