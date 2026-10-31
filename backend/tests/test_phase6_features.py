import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.security import generate_download_token, generate_job_access_token
from app.db.session import get_sync_db
from app.main import app
from app.models.job import DownloadJob, JobStatus
from app.schemas.extract import FormatOption, MediaInfoResponse


@pytest.mark.asyncio
async def test_download_deduplication():
    """Verify create_download_job returns the existing active job instead of creating a duplicate."""
    job_id = uuid.uuid4()
    target_url = "https://www.youtube.com/watch?v=dedup_test_video"
    canonical_url = "https://www.youtube.com/watch?v=dedup_test_video"
    url_hash = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()

    with get_sync_db() as db:
        existing_job = DownloadJob(
            id=job_id,
            url_hash=url_hash,
            original_url=target_url,
            title="Deduplication Target Video",
            format_id="best_1080p",
            ip_hash="test_ip_hash",
            status=JobStatus.PROCESSING,
            progress=40.0,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
        db.add(existing_job)
        db.commit()

    mock_info = MediaInfoResponse(
        id="dedup_test_video",
        title="Deduplication Target Video",
        url=target_url,
        thumbnail_url="https://img.youtube.com/vi/dedup_test_video/hqdefault.jpg",
        duration=120,
        formats=[
            FormatOption(
                format_id="best_1080p",
                resolution="1080p",
                ext="mp4",
                format_note="1080p HD",
                is_audio_only=False,
            )
        ],
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("app.api.v1.endpoints.downloads.extract_media_info", return_value=mock_info):
            resp = await client.post(
                "/api/v1/downloads",
                json={
                    "url": target_url,
                    "format_id": "best_1080p",
                    "audio_only": False,
                },
            )
            assert resp.status_code in [200, 201, 202]
            data = resp.json()
            # Must return the existing job ID rather than spawning a new UUID
            assert data["job_id"] == str(job_id)
            assert data["status"] == "PROCESSING"
            assert data["progress"] == 40.0
            assert "job_access_token" in data


@pytest.mark.asyncio
async def test_download_file_resumable_range_request(tmp_path):
    """Verify GET /downloads/{id}/file supports HTTP 206 Partial Content Range requests."""
    job_id = uuid.uuid4()
    content = b"0123456789abcdefghijklmnopqrstuvwxyz" * 10  # 360 bytes
    test_file = tmp_path / f"{job_id}.mp4"
    test_file.write_bytes(content)

    with get_sync_db() as db:
        job = DownloadJob(
            id=job_id,
            url_hash="sample_range_hash",
            original_url="https://youtube.com/watch?v=sample_range",
            title="Range Request Test Media",
            format_id="best",
            ip_hash="test_ip_hash",
            status=JobStatus.COMPLETED,
            progress=100.0,
            file_path=str(test_file),
            file_size=len(content),
            file_ext="mp4",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
        db.add(job)
        db.commit()

    token = generate_download_token(job_id=str(job_id), file_name="range_test.mp4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Request partial byte range: bytes 0-9 (10 bytes)
        resp = await client.get(
            f"/api/v1/downloads/{job_id}/file?token={token}",
            headers={"Range": "bytes=0-9"},
        )
        assert resp.status_code == 206
        assert resp.headers.get("Accept-Ranges") == "bytes"
        assert resp.headers.get("Content-Range") == f"bytes 0-9/{len(content)}"
        assert resp.content == content[0:10]


@pytest.mark.asyncio
async def test_sse_stream_endpoint():
    """Verify GET /downloads/{id}/stream returns SSE event stream with initial job state."""
    job_id = uuid.uuid4()
    with get_sync_db() as db:
        job = DownloadJob(
            id=job_id,
            url_hash="sample_sse_hash",
            original_url="https://youtube.com/watch?v=sample_sse",
            title="SSE Stream Test Video",
            format_id="1080p",
            ip_hash="test_ip_hash",
            status=JobStatus.COMPLETED,
            progress=100.0,
            file_size=5000000,
            download_url=f"/api/v1/downloads/{job_id}/file?token=mock_tok",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
        db.add(job)
        db.commit()

    token = generate_job_access_token(str(job_id))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/v1/downloads/{job_id}/stream?token={token}")
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")
        # Since status is COMPLETED, it emits the data event and terminates
        body = resp.text
        assert "data: " in body
        assert str(job_id) in body
        assert "COMPLETED" in body


@pytest.mark.asyncio
async def test_prometheus_metrics_endpoint():
    """Verify GET /metrics exposes Prometheus exposition format metrics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/metrics")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers.get("content-type", "")
        text_body = resp.text
        assert "anystream_jobs_total" in text_body
        assert "anystream_jobs_active" in text_body
        assert "anystream_cache_hits_total" in text_body
        assert "anystream_cache_misses_total" in text_body
