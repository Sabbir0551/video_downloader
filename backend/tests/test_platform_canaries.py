import yaml
from pathlib import Path
import pytest
from app.platforms.adapters import get_platform_adapter, YouTubeAdapter, TwitterAdapter
from app.platforms.resilience import PlatformCircuitBreaker

def test_canary_config_validity():
    """Verify canary YAML configuration is well-formed."""
    canary_path = Path(__file__).parent / "platform_canaries.yaml"
    assert canary_path.exists()

    with open(canary_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert "canaries" in data
    assert len(data["canaries"]) >= 5
    for c in data["canaries"]:
        assert "id" in c
        assert "platform_id" in c
        assert "url" in c


def test_platform_adapters_canonicalization():
    """Verify adapters normalize platform URLs properly."""
    yt_adapter = get_platform_adapter("youtube")
    assert isinstance(yt_adapter, YouTubeAdapter)
    short_url = yt_adapter.canonicalize_url("https://www.youtube.com/shorts/dQw4w9WgXcQ?feature=share")
    assert "https://www.youtube.com/watch?v=dQw4w9WgXcQ" == short_url

    tw_adapter = get_platform_adapter("twitter")
    assert isinstance(tw_adapter, TwitterAdapter)
    tw_url = tw_adapter.canonicalize_url("https://twitter.com/user/status/1234567890?s=20")
    assert tw_url == "https://x.com/i/status/1234567890"


def test_circuit_breaker_resilience():
    """Verify circuit breaker opens after threshold failures."""
    cb = PlatformCircuitBreaker(failure_threshold=3, cooldown_seconds=10)
    plat = "mock_failing_platform"

    # Reset
    cb.record_success(plat)
    assert cb.is_available(plat) is True

    # Record 2 failures (under threshold)
    cb.record_failure(plat)
    cb.record_failure(plat)
    assert cb.is_available(plat) is True

    # 3rd failure triggers open circuit
    cb.record_failure(plat)
    assert cb.is_available(plat) is False

    # Success resets circuit
    cb.record_success(plat)
    assert cb.is_available(plat) is True

