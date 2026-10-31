import os
import sys

# Ensure backend root is on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Set test environment flags
os.environ["ENVIRONMENT"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key-32-chars-long-minimum-safe"
os.environ["IP_HASH_SALT"] = "test-salt-for-unit-testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["DATABASE_SYNC_URL"] = "sqlite:///./test.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

import pytest
import redis
from app.core.config import settings
from app.core.rate_limit import _memory_windows
from app.db.session import get_sync_db
from app.models.base import Base


@pytest.fixture(autouse=True)
def clean_test_environment():
    """Ensures clean database and resets rate limits before each test."""
    _memory_windows.clear()
    try:
        r = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=0.2,
            socket_timeout=0.2,
        )
        keys = r.keys("ratelimit:*")
        if keys:
            r.delete(*keys)
    except Exception:
        pass

    with get_sync_db() as db:
        try:
            from sqlalchemy import text
            db.execute(text("DELETE FROM abuse_logs"))
            db.execute(text("DELETE FROM download_jobs"))
            db.execute(text("DELETE FROM takedown_records"))
            db.commit()
        except Exception:
            db.rollback()
            Base.metadata.create_all(bind=db.bind)

    yield

    _memory_windows.clear()
    try:
        r = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=0.2,
            socket_timeout=0.2,
        )
        keys = r.keys("ratelimit:*")
        if keys:
            r.delete(*keys)
    except Exception:
        pass


