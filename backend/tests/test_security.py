import time
import pytest

from app.core.errors import DownloadTokenInvalidError
from app.core.security import (
    generate_download_token,
    hash_ip,
    sanitize_filename,
    verify_download_token,
)


def test_ip_hashing():
    """Verify IP hashing is deterministic with same salt and does not reveal IP."""
    ip = "192.168.1.100"
    salt = "secret-test-salt"
    hashed_1 = hash_ip(ip, salt=salt)
    hashed_2 = hash_ip(ip, salt=salt)
    assert hashed_1 == hashed_2
    assert ip not in hashed_1
    assert len(hashed_1) == 32

    # Different salt yields different hash
    assert hash_ip(ip, salt="alt-salt") != hashed_1


def test_sanitize_filename_path_traversal():
    """Verify directory traversal tokens and forbidden characters are stripped."""
    dangerous = "../../etc/passwd"
    clean = sanitize_filename(dangerous, "mp4")
    assert "/" not in clean
    assert "\\" not in clean
    assert ".." not in clean
    assert clean.endswith(".mp4")


def test_sanitize_filename_forbidden_symbols():
    """Verify characters invalid on POSIX/Windows are replaced."""
    dirty = 'Video: "Best Of" <2026> | Top * Hits? & More!'
    clean = sanitize_filename(dirty, "mp4")
    for bad_char in [':', '"', '<', '>', '|', '*', '?']:
        assert bad_char not in clean


def test_sanitize_filename_reserved_windows_names():
    """Verify Windows reserved file names like CON or PRN are neutralized."""
    clean = sanitize_filename("CON", "mp4")
    assert clean == "CON_file.mp4"

    clean_prn = sanitize_filename("prn", "mp3")
    assert clean_prn == "prn_file.mp3"


def test_sanitize_filename_unicode_and_truncation():
    """Verify unicode characters are handled properly and length is constrained."""
    long_title = "বাংলা গান " + ("A" * 200)
    clean = sanitize_filename(long_title, "m4a", max_length=50)
    assert len(clean) <= 54  # 50 chars + .m4a
    assert "বাংলা" in clean


def test_download_token_lifecycle():
    """Verify token generation, signature verification, and payload extraction."""
    job_id = "550e8400-e29b-41d4-a716-446655440000"
    file_name = "test_video.mp4"

    token = generate_download_token(job_id=job_id, file_name=file_name, expiry_seconds=60)
    assert isinstance(token, str)
    assert "." in token

    payload = verify_download_token(token)
    assert payload["job_id"] == job_id
    assert payload["file_name"] == file_name
    assert payload["exp"] > time.time()


def test_download_token_tampering():
    """Verify tampered payload fails signature validation."""
    job_id = "550e8400-e29b-41d4-a716-446655440000"
    token = generate_download_token(job_id=job_id, file_name="video.mp4", expiry_seconds=60)

    # Tamper with the token
    payload_part, sig_part = token.split(".")
    tampered_token = f"extra_{payload_part}.{sig_part}"

    with pytest.raises(DownloadTokenInvalidError):
        verify_download_token(tampered_token)


def test_download_token_expired():
    """Verify expired token raises exception."""
    job_id = "550e8400-e29b-41d4-a716-446655440000"
    # Generate token already expired (-5 seconds)
    token = generate_download_token(job_id=job_id, file_name="video.mp4", expiry_seconds=-5)

    with pytest.raises(DownloadTokenInvalidError) as exc_info:
        verify_download_token(token)
    assert "expired" in exc_info.value.message


def test_ip_spoofing_rejected_from_untrusted_peer():
    """Verify that an untrusted direct peer cannot spoof client IP via X-Forwarded-For."""
    from unittest.mock import MagicMock
    from app.core.rate_limit import get_raw_client_ip

    # Peer is an untrusted public IP
    req = MagicMock()
    req.client.host = "198.51.100.55"
    req.headers.get.return_value = "203.0.113.1"  # Spoofed attempt

    # Since peer 198.51.100.55 is not in TRUSTED_PROXIES, X-Forwarded-For must be ignored
    resolved_ip = get_raw_client_ip(req)
    assert resolved_ip == "198.51.100.55"


def test_ip_forwarded_for_from_trusted_proxy():
    """Verify that trusted proxy hops are traversed to the right-most untrusted client IP."""
    from unittest.mock import MagicMock
    from app.core.rate_limit import get_raw_client_ip

    req = MagicMock()
    req.client.host = "127.0.0.1"  # Trusted proxy
    req.headers.get.return_value = "203.0.113.88, 127.0.0.1"

    resolved_ip = get_raw_client_ip(req)
    assert resolved_ip == "203.0.113.88"


def test_job_access_token_verification():
    """Verify cryptographic job access token generation and tamper protection."""
    from app.core.security import generate_job_access_token, verify_job_access_token

    job_id = "550e8400-e29b-41d4-a716-446655440000"
    token = generate_job_access_token(job_id)

    assert token.startswith("jat_")
    assert verify_job_access_token(token, job_id) is True
    # Fails for different job ID
    assert verify_job_access_token(token, "660e8400-e29b-41d4-a716-446655440000") is False
    # Fails for tampered token
    assert verify_job_access_token(token + "tamper", job_id) is False


def test_url_normalization_canonicalization():
    """Verify YouTube and tracking URLs are normalized to prevent takedown bypass."""
    from app.core.security import normalize_video_url

    url1 = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&feature=share&si=123"
    canon1, id1 = normalize_video_url(url1)
    assert canon1 == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert id1 == "youtube:dQw4w9WgXcQ"

    url2 = "https://youtu.be/dQw4w9WgXcQ?utm_source=twitter"
    canon2, id2 = normalize_video_url(url2)
    assert canon2 == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert id2 == "youtube:dQw4w9WgXcQ"


def test_production_secret_validation():
    """Verify Settings refuses to initialize in production with default/short secrets."""
    from app.core.config import Settings

    with pytest.raises(ValueError, match="FATAL SECURITY"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="insecure-dev-secret-key",
            IP_HASH_SALT="dev-salt-short",
        )


