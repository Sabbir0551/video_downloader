import hashlib
import ipaddress
import os
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.db.session import async_engine, get_sync_db
from app.main import app
from app.models.base import Base
from app.models.job import DownloadJob, JobStatus
from app.models.takedown import TakedownRecord, TakedownStatus
from app.schemas.extract import FormatOption, MediaInfoResponse


@pytest.fixture(autouse=True)
def setup_test_db():
    """Ensures database tables are initialized for testing."""
    with get_sync_db() as db:
        Base.metadata.create_all(bind=db.bind)
    yield


@pytest.fixture
def mock_dns_resolution(monkeypatch):
    """Mocks DNS resolution so public URLs pass SSRF verification."""
    def _mock_resolve(hostname: str):
        return [ipaddress.ip_address("142.250.190.46")]
    monkeypatch.setattr("app.core.ssrf.resolve_hostname_ips", _mock_resolve)


@pytest.fixture
def sample_media_info():
    """Mocked extracted media info for valid video."""
    return MediaInfoResponse(
        id="test_media_123",
        title="Sample Test Video",
        url="https://www.youtube.com/watch?v=sample123",
        thumbnail_url="https://img.youtube.com/vi/sample123/hqdefault.jpg",
        duration=180,
        uploader="Test Creator",
        is_live=False,
        formats=[
            FormatOption(
                format_id="137+140",
                resolution="1080p",
                height=1080,
                fps=30.0,
                ext="mp4",
                format_note="1080p Full HD",
                filesize_approx=50000000,
                is_audio_only=False,
            )
        ],
    )


@pytest.mark.asyncio
async def test_create_download_job_success(mock_dns_resolution, sample_media_info):
    """Verify POST /api/v1/downloads enqueues job and returns 202 Accepted."""
    with patch("app.api.v1.endpoints.downloads.extract_media_info", return_value=sample_media_info), \
         patch("app.api.v1.endpoints.downloads.download_media_task.delay") as mock_delay:

        mock_delay.return_value = MagicMock(id="celery-task-id-123")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/downloads",
                json={
                    "url": "https://www.youtube.com/watch?v=sample123",
                    "format_id": "137+140",
                    "audio_only": False,
                    "quality_label": "1080p",
                },
            )

            assert resp.status_code == 202
            data = resp.json()
            assert "job_id" in data
            assert data["status"] == "QUEUED"
            assert data["progress"] == 0.0

            # Verify Celery delay was called with correct arguments
            mock_delay.assert_called_once()
            call_kwargs = mock_delay.call_args[1]
            assert call_kwargs["url"] == "https://www.youtube.com/watch?v=sample123"
            assert call_kwargs["format_id"] == "137+140"
            assert call_kwargs["is_audio_only"] is False


@pytest.mark.asyncio
async def test_create_download_job_ssrf_blocked():
    """Verify private/internal URLs are rejected with 400 before enqueuing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/downloads",
            json={
                "url": "http://127.0.0.1:8000/admin",
                "format_id": "137+140",
            },
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "SSRF_DESTINATION_FORBIDDEN"


@pytest.mark.asyncio
async def test_create_download_job_takedown_blocked(mock_dns_resolution):
    """Verify copyright blocked URL returns 451 Unavailable For Legal Reasons."""
    target_url = "https://www.youtube.com/watch?v=copyrighted_infringing"
    url_hash = hashlib.sha256(target_url.encode("utf-8")).hexdigest()

    # Insert a takedown record into DB
    with get_sync_db() as db:
        takedown = TakedownRecord(
            url_hash=url_hash,
            target_url=target_url,
            copyrighted_work_url="https://original.com/work",
            requester_name="Owner",
            requester_email="owner@copyright.org",
            status=TakedownStatus.BLOCKED_PENDING_REVIEW,
        )
        db.add(takedown)
        db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/downloads",
            json={
                "url": target_url,
                "format_id": "137+140",
            },
        )
        assert resp.status_code == 451
        data = resp.json()
        assert data["error_code"] == "LEGAL_TAKEDOWN_BLOCK"


@pytest.mark.asyncio
async def test_create_download_job_duration_exceeded(mock_dns_resolution, sample_media_info):
    """Verify video exceeding duration limit is rejected."""
    sample_media_info.duration = 15000  # > 3 hours
    with patch("app.api.v1.endpoints.downloads.extract_media_info", return_value=sample_media_info):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/downloads",
                json={
                    "url": "https://www.youtube.com/watch?v=sample123",
                    "format_id": "137+140",
                },
            )
            assert resp.status_code == 400
            assert resp.json()["error_code"] == "MEDIA_LIMIT_EXCEEDED"


def test_celery_task_worker_execution(tmp_path):
    """
    Directly tests the Celery task execution logic:
    - Verifies file output template uses random job_id (never user title).
    - Verifies file size calculation and signed token generation.
    - Verifies job state transition in DB to COMPLETED.
    """
    from app.worker.tasks import download_media_task

    test_job_id = str(uuid.uuid4())
    test_url = "https://www.youtube.com/watch?v=dummy"
    test_title = "My User Video Title"

    # Create dummy job in DB
    with get_sync_db() as db:
        job = DownloadJob(
            id=uuid.UUID(test_job_id),
            url_hash="hash123",
            original_url=test_url,
            title=test_title,
            format_id="137+140",
            ip_hash="test_ip_hash",
            status=JobStatus.QUEUED,
        )
        db.add(job)
        db.commit()

    # Mock yt_dlp.YoutubeDL in worker
    with patch("yt_dlp.YoutubeDL") as mock_ydl_cls:
        mock_ydl_instance = MagicMock()
        mock_ydl_cls.return_value.__enter__.return_value = mock_ydl_instance

        # Simulate download creating file in storage dir
        def mock_download(urls):
            dummy_file = os.path.join(settings.STORAGE_DIR, f"{test_job_id}.mp4")
            with open(dummy_file, "wb") as f:
                f.write(b"dummy mp4 video binary content" * 100)

        mock_ydl_instance.download.side_effect = mock_download

        result = download_media_task(
            job_id=test_job_id,
            url=test_url,
            format_id="137+140",
            is_audio_only=False,
            title=test_title,
        )

        assert result["status"] == "COMPLETED"
        assert result["progress"] == 100.0
        assert "download_url" in result

        # Check ytdl_opts outtmpl used random job_id, NOT video title
        ydl_opts_used = mock_ydl_cls.call_args[0][0]
        assert test_job_id in ydl_opts_used["outtmpl"]
        assert test_title not in ydl_opts_used["outtmpl"]

        # Verify DB updated
        with get_sync_db() as db:
            updated_job = db.get(DownloadJob, uuid.UUID(test_job_id))
            assert updated_job.status == JobStatus.COMPLETED
            assert updated_job.file_size > 0
            assert updated_job.download_url.startswith("/api/v1/downloads/")

        # Clean up created dummy file
        dummy_file = os.path.join(settings.STORAGE_DIR, f"{test_job_id}.mp4")
        if os.path.exists(dummy_file):
            os.remove(dummy_file)

