import time
import uuid
from typing import Dict, List, Optional, Tuple

import redis
from fastapi import Request

from app.core.config import settings
from app.core.errors import AppError, GlobalConcurrencyExceededError, RateLimitExceededError
from app.core.security import hash_ip

# Optional Redis connection for distributed rate limiting
try:
    redis_client = redis.Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=0.5,
        socket_timeout=0.5,
    )
except Exception:
    redis_client = None

# In-memory sliding window fallback (useful for tests or standalone runs without Redis)
_memory_windows: Dict[str, List[float]] = {}


def check_rate_limit(
    ip_hash: str,
    endpoint_key: str,
    max_requests: int,
    window_seconds: int = 60,
) -> None:
    """
    Applies sliding window rate limiting for a hashed IP address.
    Never stores or logs the raw IP address.
    """
    now = time.time()
    key = f"ratelimit:{endpoint_key}:{ip_hash}"

    # 1. Try Redis sliding window
    if redis_client:
        try:
            unique_member = f"{now}:{uuid.uuid4().hex[:12]}"
            pipe = redis_client.pipeline()
            # Remove timestamps outside the sliding window
            pipe.zremrangebyscore(key, 0, now - window_seconds)
            # Add unique entry with current timestamp as score
            pipe.zadd(key, {unique_member: now})
            # Count elements in window
            pipe.zcard(key)
            # Set TTL on key
            pipe.expire(key, window_seconds + 5)
            _, _, count, _ = pipe.execute()

            if count > max_requests:
                raise RateLimitExceededError(
                    f"Too many requests to /{endpoint_key}. Rate limit is {max_requests} per minute.",
                    details={"limit": max_requests, "window_seconds": window_seconds},
                )
            return
        except RateLimitExceededError:
            raise
        except Exception:
            # Fall back to in-memory on redis connection issues
            pass

    # 2. In-memory sliding window fallback
    timestamps = _memory_windows.setdefault(key, [])
    # Prune old timestamps
    cutoff = now - window_seconds
    _memory_windows[key] = [t for t in timestamps if t > cutoff]
    if len(_memory_windows[key]) >= max_requests:
        raise RateLimitExceededError(
            f"Too many requests to /{endpoint_key}. Rate limit is {max_requests} per minute.",
            details={"limit": max_requests, "window_seconds": window_seconds},
        )
    _memory_windows[key].append(now)


def get_client_ip_hash(request: Request) -> str:
    """Extracts client IP from request and returns a privacy-preserving salted HMAC hash."""
    client_ip = "127.0.0.1"
    if request.client and request.client.host:
        client_ip = request.client.host
    # Honor X-Forwarded-For if behind trusted proxy
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    return hash_ip(client_ip)
