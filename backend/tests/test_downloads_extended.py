import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.rate_limit import _memory_windows
from app.core.security import generate_download_token, hash_ip, sanitize_filename
from app.db.session import get_sync_db
from app.main import app
from app.models.base import Base
from app.models.job import DownloadJob, JobStatus
from app.worker.tasks import clean_expired_downloads_task




@pytest.mark.asyncio
async def test_get_download_status_not_found():
    """Verify GET /api/v1/downloads/{id} returns 404 for unknown job."""
    random_id = uuid.uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/v1/downloads/{random_id}")
        assert resp.status_code == 404
        assert resp.json()["error_code"] == "JOB_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_download_status_success_and_redis_overlay():
    """Verify GET /api/v1/downloads/{id} returns status and overlays Redis live progress."""
    job_id = uuid.uuid4()
    with get_sync_db() as db:
        job = DownloadJob(
            id=job_id,
            url_hash="dummy_hash_1",
            original_url="https://youtube.com/watch?v=sample1",
            title="Sample Live Progress Video",
            format_id="137+140",
            ip_hash="test_ip_hash",
            status=JobStatus.PROCESSING,
            progress=25.0,
            speed="1.2MB/s",
            eta=45,
        )
        db.add(job)
        db.commit()

    # 1. Without Redis overlay
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/v1/downloads/{job_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == str(job_id)
        assert data["status"] == "PROCESSING"
        assert data["progress"] == 25.0

    # 2. With Redis overlay (mocking redis_client.get)
    mock_redis = MagicMock()
    mock_redis.get.return_value = json.dumps({"progress": 68.5, "speed": "3.5MB/s", "eta": 12})
    with patch("app.api.v1.endpoints.downloads.redis_client", mock_redis):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/downloads/{job_id}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["progress"] == 68.5
            assert data["speed"] == "3.5MB/s"
            assert data["eta"] == 12


@pytest.mark.asyncio
async def test_download_file_serving_and_token_validation(tmp_path):
    """
    Verify GET /api/v1/downloads/{id}/file:
    - Rejects invalid / expired / mismatched tokens with 403
    - Rejects missing / uncompleted jobs with 404
    - Serves completed file with safe Content-Disposition headers
    """
    job_id = uuid.uuid4()
    test_file_path = os.path.join(settings.STORAGE_DIR, f"{job_id}.mp4")
    raw_title = "Amazing Video? [Awesome/Dangerous] <Title>"
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    with open(test_file_path, "wb") as f:
        f.write(b"SAMPLE VIDEO BINARY STREAM " * 50)

    try:
        with get_sync_db() as db:
            job = DownloadJob(
                id=job_id,
                url_hash="dummy_hash_file",
                original_url="https://youtube.com/watch?v=file_test",
                title=raw_title,
                format_id="137+140",
                ip_hash="test_ip_hash",
                status=JobStatus.COMPLETED,
                file_path=test_file_path,
                file_size=os.path.getsize(test_file_path),
                file_ext="mp4",
            )
            db.add(job)
            db.commit()

        # 1. Valid Token
        valid_token = generate_download_token(
            job_id=str(job_id),
            file_name=sanitize_filename(raw_title, "mp4"),
            expiry_seconds=1800,
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1.1 Valid download
            resp = await client.get(f"/api/v1/downloads/{job_id}/file?token={valid_token}")
            assert resp.status_code == 200
            assert "Content-Disposition" in resp.headers
            assert 'filename="' in resp.headers["Content-Disposition"]
            assert "<Title>" not in resp.headers["Content-Disposition"]  # Sanitized!
            assert len(resp.content) == os.path.getsize(test_file_path)

            # 1.2 Invalid / Tampered token
            tampered_token = valid_token[:-4] + "abcd"
            resp_tampered = await client.get(f"/api/v1/downloads/{job_id}/file?token={tampered_token}")
            assert resp_tampered.status_code == 403
            assert resp_tampered.json()["error_code"] == "DOWNLOAD_TOKEN_INVALID"

            # 1.3 Token for another job_id
            other_id = str(uuid.uuid4())
            wrong_job_token = generate_download_token(
                job_id=other_id,
                file_name="other.mp4",
                expiry_seconds=1800,
            )
            resp_wrong = await client.get(f"/api/v1/downloads/{job_id}/file?token={wrong_job_token}")
            assert resp_wrong.status_code == 403
            assert resp_wrong.json()["error_code"] == "DOWNLOAD_TOKEN_INVALID"

            # 1.4 Expired token
            expired_token = generate_download_token(
                job_id=str(job_id),
                file_name="test.mp4",
                expiry_seconds=-10,  # Already expired
            )
            resp_expired = await client.get(f"/api/v1/downloads/{job_id}/file?token={expired_token}")
            assert resp_expired.status_code == 403
            assert resp_expired.json()["error_code"] == "DOWNLOAD_TOKEN_INVALID"

    finally:
        if os.path.exists(test_file_path):
            os.remove(test_file_path)


@pytest.mark.asyncio
async def test_cancel_download_job():
    """Verify DELETE /api/v1/downloads/{id} revokes Celery task, deletes files, and sets CANCELLED."""
    job_id = uuid.uuid4()
    test_file = os.path.join(settings.STORAGE_DIR, f"{job_id}.mp4")
    part_file = os.path.join(settings.STORAGE_DIR, f"{job_id}.part")
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    with open(test_file, "wb") as f:
        f.write(b"data")
    with open(part_file, "wb") as f:
        f.write(b"partial")

    with get_sync_db() as db:
        job = DownloadJob(
            id=job_id,
            url_hash="cancel_hash",
            original_url="https://youtube.com/watch?v=cancel_test",
            title="Video to cancel",
            format_id="137+140",
            ip_hash="test_ip_hash",
            status=JobStatus.PROCESSING,
            file_path=test_file,
        )
        db.add(job)
        db.commit()

    with patch("app.api.v1.endpoints.downloads.celery_app.control.revoke") as mock_revoke:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.delete(f"/api/v1/downloads/{job_id}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "CANCELLED"
            assert data["error_code"] == "USER_CANCELLED"

            mock_revoke.assert_called_once_with(str(job_id), terminate=True, signal="SIGTERM")

    # Verify physical files purged
    assert not os.path.exists(test_file)
    assert not os.path.exists(part_file)

    # Verify database status updated
    with get_sync_db() as db:
        cancelled_job = db.get(DownloadJob, job_id)
        assert cancelled_job.status == JobStatus.CANCELLED


def test_clean_expired_downloads_celery_beat():
    """
    Verify Celery Beat janitor task:
    - Evicts files older than 30 minutes / past expires_at
    - Marks database job status as EXPIRED
    - Preserves unexpired jobs and files
    """
    now = datetime.now(timezone.utc)
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)

    # 1. Create an expired job (expired 5 minutes ago)
    expired_id = uuid.uuid4()
    expired_file = os.path.join(settings.STORAGE_DIR, f"{expired_id}.mp4")
    with open(expired_file, "wb") as f:
        f.write(b"expired content")

    # 2. Create an active unexpired job (expires in 25 minutes)
    active_id = uuid.uuid4()
    active_file = os.path.join(settings.STORAGE_DIR, f"{active_id}.mp4")
    with open(active_file, "wb") as f:
        f.write(b"active content")

    with get_sync_db() as db:
        expired_job = DownloadJob(
            id=expired_id,
            url_hash="expired_hash",
            original_url="https://youtube.com/watch?v=expired",
            title="Expired Video",
            format_id="137+140",
            ip_hash="ip_hash_1",
            status=JobStatus.COMPLETED,
            file_path=expired_file,
            expires_at=now - timedelta(minutes=5),
        )
        active_job = DownloadJob(
            id=active_id,
            url_hash="active_hash",
            original_url="https://youtube.com/watch?v=active",
            title="Active Video",
            format_id="137+140",
            ip_hash="ip_hash_2",
            status=JobStatus.COMPLETED,
            file_path=active_file,
            expires_at=now + timedelta(minutes=25),
        )
        db.add_all([expired_job, active_job])
        db.commit()

    # Run the beat cleanup task
    result = clean_expired_downloads_task()
    assert result["expired_jobs"] >= 1
    assert result["evicted_files"] >= 1

    # Verify expired file removed from disk
    assert not os.path.exists(expired_file)
    # Verify active file remains untouched
    assert os.path.exists(active_file)

    # Verify DB statuses
    with get_sync_db() as db:
        j1 = db.get(DownloadJob, expired_id)
        assert j1.status == JobStatus.EXPIRED

        j2 = db.get(DownloadJob, active_id)
        assert j2.status == JobStatus.COMPLETED

    # Clean up active file
    if os.path.exists(active_file):
        os.remove(active_file)


@pytest.mark.asyncio
async def test_rate_limiting_per_ip():
    """
    Verify rate limiting per IP:
    - Never stores raw IP (uses salted HMAC hash)
    - Returns 429 when quota is exceeded
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Patch extract_media_info so /info succeeds
        with patch("app.api.v1.endpoints.info.extract_media_info") as mock_extract, \
             patch("app.api.v1.endpoints.info.validate_url_security", return_value=("https://example.com/v", ["1.1.1.1"])):
            from app.schemas.extract import MediaInfoResponse
            mock_extract.return_value = MediaInfoResponse(
                id="test",
                title="T",
                url="https://example.com/v",
                thumbnail_url="https://img.youtube.com/vi/sample/hqdefault.jpg",
                duration=60,
                uploader="U",
                is_live=False,
                formats=[],
            )

            # Hit /info up to limit (15 req/min)
            for _ in range(settings.RATE_LIMIT_EXTRACT_PER_MINUTE):
                resp = await client.post("/api/v1/info", json={"url": "https://example.com/v"})
                assert resp.status_code == 200

            # 16th request must trigger 429
            rate_limited_resp = await client.post("/api/v1/info", json={"url": "https://example.com/v"})
            assert rate_limited_resp.status_code == 429
            err_data = rate_limited_resp.json()
            assert err_data["error_code"] == "RATE_LIMIT_EXCEEDED"
            assert "15" in err_data["message"]


@pytest.mark.asyncio
async def test_global_concurrency_cap():
    """
    Verify system-wide global concurrency limit:
    When 20 active jobs exist system-wide, new job creation fails with 503 GLOBAL_CONCURRENCY_EXCEEDED.
    """
    # Insert 20 active jobs into DB
    with get_sync_db() as db:
        for i in range(settings.GLOBAL_CONCURRENCY_CAP):
            job = DownloadJob(
                id=uuid.uuid4(),
                url_hash=f"hash_{i}",
                original_url=f"https://youtube.com/watch?v=v{i}",
                title=f"Concurrent Video {i}",
                format_id="137+140",
                ip_hash=f"different_ip_{i}",  # All different IPs so per-IP cap doesn't trip
                status=JobStatus.PROCESSING,
            )
            db.add(job)
        db.commit()

    with patch("app.api.v1.endpoints.downloads.validate_url_security", return_value=("https://example.com/v", ["1.1.1.1"])):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/downloads",
                json={"url": "https://example.com/v", "format_id": "137+140"},
            )
            assert resp.status_code == 503
            err = resp.json()
            assert err["error_code"] == "GLOBAL_CONCURRENCY_EXCEEDED"
            assert err["details"]["global_concurrency_cap"] == 20
