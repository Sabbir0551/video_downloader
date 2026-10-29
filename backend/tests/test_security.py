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

