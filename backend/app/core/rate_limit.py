import ipaddress
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


def get_raw_client_ip(request: Request) -> str:
    """
    Extracts validated client IP from request, taking the right-most untrusted hop
    when forwarded by trusted proxies. Never trusts untrusted clients.
    """
    peer_ip = "127.0.0.1"
    if request.client and request.client.host:
        peer_ip = request.client.host

    # Check if peer is in trusted proxies
    is_peer_trusted = False
    try:
        peer_obj = ipaddress.ip_address(peer_ip)
        for tp in settings.TRUSTED_PROXIES:
            try:
                if "/" in tp:
                    if peer_obj in ipaddress.ip_network(tp):
                        is_peer_trusted = True
                        break
                else:
                    if peer_obj == ipaddress.ip_address(tp):
                        is_peer_trusted = True
                        break
            except ValueError:
                continue
    except ValueError:
        pass

    forwarded_for = request.headers.get("X-Forwarded-For")
    if not is_peer_trusted or not forwarded_for or settings.TRUSTED_PROXY_COUNT <= 0:
        return peer_ip

    # Parse hops: "client, proxy1, proxy2"
    hops = [h.strip() for h in forwarded_for.split(",") if h.strip()]
    if not hops:
        return peer_ip

    # Walk backwards from the rightmost hop (closest to our trusted proxy)
    # The first untrusted IP encountered is the real client IP.
    for hop in reversed(hops):
        try:
            hop_obj = ipaddress.ip_address(hop)
            hop_is_trusted = False
            for tp in settings.TRUSTED_PROXIES:
                try:
                    if "/" in tp:
                        if hop_obj in ipaddress.ip_network(tp):
                            hop_is_trusted = True
                            break
                    else:
                        if hop_obj == ipaddress.ip_address(tp):
                            hop_is_trusted = True
                            break
                except ValueError:
                    continue
            if not hop_is_trusted:
                return hop
        except ValueError:
            continue

    return hops[0] if hops else peer_ip


def get_client_ip_hash(request: Request) -> str:
    """Extracts client IP from request and returns a privacy-preserving salted HMAC hash."""
    return hash_ip(get_raw_client_ip(request))
