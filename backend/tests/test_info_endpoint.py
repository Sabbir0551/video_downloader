import ipaddress
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from yt_dlp.utils import DownloadError

from app.main import app


@pytest.fixture
def mock_public_dns(monkeypatch):
    """Mocks DNS resolution so public domains pass SSRF pre-checks without external network calls."""
    def _mock_resolve(hostname: str):
        return [ipaddress.ip_address("142.250.190.46")]

    monkeypatch.setattr("app.core.ssrf.resolve_hostname_ips", _mock_resolve)


@pytest.fixture
def sample_ytdlp_info():
    """Generates standard mocked yt-dlp metadata."""
    return {
        "id": "dQw4w9WgXcQ",
        "title": "Rick Astley - Never Gonna Give You Up (Official Music Video)",
        "webpage_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
        "duration": 213,
        "uploader": "Rick Astley",
        "is_live": False,
        "has_drm": False,
        "formats": [
            # 1080p video-only stream
            {
                "format_id": "137",
                "ext": "mp4",
                "height": 1080,
                "fps": 60,
                "vcodec": "avc1.64002a",
                "acodec": "none",
                "vbr": 3500.0,
                "filesize": 75000000,
            },
            # 720p progressive video+audio stream
            {
                "format_id": "22",
                "ext": "mp4",
                "height": 720,
                "fps": 30,
                "vcodec": "avc1.4d401f",
                "acodec": "mp4a.40.2",
                "tbr": 1800.0,
                "filesize": 45000000,
                "abr": 128.0,
            },
            # 480p video-only stream
            {
                "format_id": "135",
                "ext": "mp4",
                "height": 480,
                "fps": 30,
                "vcodec": "avc1.4d401e",
                "acodec": "none",
                "vbr": 900.0,
                "filesize": 25000000,
            },
            # Best audio-only stream
            {
                "format_id": "140",
                "ext": "m4a",
                "vcodec": "none",
                "acodec": "mp4a.40.2",
                "abr": 128.0,
                "filesize": 3400000,
            },
        ],
    }


@pytest.mark.asyncio
async def test_health_endpoints_and_security_headers():
    """Verify /health returns 200 and enforces secure HTTP headers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "ytdlp_version" in data

        # Check security headers
        headers = resp.headers
        assert headers["x-content-type-options"] == "nosniff"
        assert headers["x-frame-options"] == "DENY"
        assert "strict-origin" in headers["referrer-policy"]
        assert "default-src 'self'" in headers["content-security-policy"]

        # Also verify prefix /api/v1/health
        api_resp = await client.get("/api/v1/health")
        assert api_resp.status_code == 200


@pytest.mark.asyncio
async def test_info_endpoint_success(mock_public_dns, sample_ytdlp_info):
    """Verify POST /api/v1/info returns structured metadata and normalized formats."""
    with patch("yt_dlp.YoutubeDL") as mock_ydl_cls:
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = sample_ytdlp_info
        mock_ydl_cls.return_value.__enter__.return_value = mock_ydl_instance

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/info",
                json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
            )
            assert resp.status_code == 200
            data = resp.json()

            assert data["id"] == "dQw4w9WgXcQ"
            assert "Rick Astley" in data["title"]
            assert data["duration"] == 213
            assert data["uploader"] == "Rick Astley"
            assert data["is_live"] is False

            formats = data["formats"]
            assert len(formats) > 0

            # 1080p should be multiplexed with audio (137+140)
            fmt_1080 = next((f for f in formats if f["height"] == 1080), None)
            assert fmt_1080 is not None
            assert fmt_1080["format_id"] == "137+140"
            assert fmt_1080["resolution"] == "1080p"
            assert fmt_1080["ext"] == "mp4"
            assert fmt_1080["filesize_approx"] == (75000000 + 3400000)

            # Audio-only options
            audio_m4a = next((f for f in formats if f["ext"] == "m4a" and f["is_audio_only"]), None)
            assert audio_m4a is not None
            assert audio_m4a["format_id"] == "140"

            audio_mp3 = next((f for f in formats if f["ext"] == "mp3" and f["is_audio_only"]), None)
            assert audio_mp3 is not None
            assert "140+mp3" in audio_mp3["format_id"]


@pytest.mark.asyncio
async def test_info_endpoint_ssrf_rejection():
    """Verify SSRF attacks are blocked before reaching extraction."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Loopback
        resp = await client.post("/api/v1/info", json={"url": "http://127.0.0.1:8000/secret"})
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "SSRF_DESTINATION_FORBIDDEN"

        # Cloud Metadata
        resp_meta = await client.post("/api/v1/info", json={"url": "http://169.254.169.254/latest/meta-data"})
        assert resp_meta.status_code == 400
        assert resp_meta.json()["error_code"] == "SSRF_DESTINATION_FORBIDDEN"

        # Invalid Scheme
        resp_file = await client.post("/api/v1/info", json={"url": "file:///etc/passwd"})
        assert resp_file.status_code == 422


@pytest.mark.asyncio
async def test_info_endpoint_drm_rejection(mock_public_dns):
    """Verify DRM protected content returns 403 Forbidden with clear error."""
    with patch("yt_dlp.YoutubeDL") as mock_ydl_cls:
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.side_effect = DownloadError("This video is DRM protected and cannot be processed.")
        mock_ydl_cls.return_value.__enter__.return_value = mock_ydl_instance

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/info",
                json={"url": "https://www.netflix.com/watch/12345"},
            )
            assert resp.status_code == 403
            data = resp.json()
            assert data["error_code"] == "MEDIA_DRM_PROTECTED"
            assert "DRM" in data["message"]


@pytest.mark.asyncio
async def test_info_endpoint_private_video_error_mapping(mock_public_dns):
    """Verify private video yt-dlp error is mapped to a friendly user message."""
    with patch("yt_dlp.YoutubeDL") as mock_ydl_cls:
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.side_effect = DownloadError("Private video. Sign in if you've been granted access to this video")
        mock_ydl_cls.return_value.__enter__.return_value = mock_ydl_instance

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/info",
                json={"url": "https://www.youtube.com/watch?v=private_id"},
            )
            assert resp.status_code == 400
            data = resp.json()
            assert data["error_code"] == "UNSUPPORTED_URL_OR_PLATFORM"
            assert "private" in data["message"].lower()


@pytest.mark.asyncio
async def test_info_endpoint_duration_limit_exceeded(mock_public_dns, sample_ytdlp_info):
    """Verify videos exceeding 3 hours are rejected with MEDIA_LIMIT_EXCEEDED."""
    sample_ytdlp_info["duration"] = 14400  # 4 hours
    with patch("yt_dlp.YoutubeDL") as mock_ydl_cls:
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = sample_ytdlp_info
        mock_ydl_cls.return_value.__enter__.return_value = mock_ydl_instance

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/info",
                json={"url": "https://www.youtube.com/watch?v=very_long_video"},
            )
            assert resp.status_code == 400
            data = resp.json()
            assert data["error_code"] == "MEDIA_LIMIT_EXCEEDED"
            assert "exceeds" in data["message"]


@pytest.mark.asyncio
async def test_info_endpoint_livestream_rejection(mock_public_dns, sample_ytdlp_info):
    """Verify active livestreams are rejected."""
    sample_ytdlp_info["is_live"] = True
    with patch("yt_dlp.YoutubeDL") as mock_ydl_cls:
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = sample_ytdlp_info
        mock_ydl_cls.return_value.__enter__.return_value = mock_ydl_instance

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/info",
                json={"url": "https://www.youtube.com/watch?v=live_stream_id"},
            )
            assert resp.status_code == 400
            data = resp.json()
            assert "live" in data["message"].lower()


@pytest.mark.asyncio
async def test_info_endpoint_takedown_blocked_and_admin_review(mock_public_dns):
    """Verify legal takedown blocks /info extraction and admin API can review it."""
    import hashlib
    import uuid
    from app.db.session import get_sync_db
    from app.models.takedown import TakedownRecord, TakedownStatus
    from app.core.config import settings

    target_url = "https://www.youtube.com/watch?v=copyright_violation_123"
    url_hash = hashlib.sha256(target_url.encode("utf-8")).hexdigest()
    case_id = uuid.uuid4()

    # 1. Insert takedown record
    with get_sync_db() as db:
        rec = TakedownRecord(
            id=case_id,
            url_hash=url_hash,
            target_url=target_url,
            channel_id="youtube:copyright_violation_123",
            copyrighted_work_url="https://original.com",
            requester_name="Copyright Owner",
            requester_email="owner@copyright.com",
            status=TakedownStatus.BLOCKED_PENDING_REVIEW,
        )
        db.add(rec)
        db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 2. Check /info is blocked with 451
        resp = await client.post("/api/v1/info", json={"url": target_url})
        assert resp.status_code == 451
        assert resp.json()["error_code"] == "LEGAL_TAKEDOWN_BLOCK"

        # Check URL variant (youtu.be) is also blocked
        variant_url = "https://youtu.be/copyright_violation_123?utm_source=twitter"
        resp_var = await client.post("/api/v1/info", json={"url": variant_url})
        assert resp_var.status_code == 451

        # 3. Test Admin API list takedowns
        admin_resp = await client.get(
            "/api/v1/admin/takedowns",
            headers={"X-Admin-Key": settings.ADMIN_API_KEY},
        )
        assert admin_resp.status_code == 200
        cases = admin_resp.json()
        assert any(c["id"] == str(case_id) for c in cases)

        # 4. Admin rejects takedown
        review_resp = await client.post(
            f"/api/v1/admin/takedowns/{case_id}/review",
            headers={"X-Admin-Key": settings.ADMIN_API_KEY},
            json={"action": "reject", "notes": "Fair use authorized"},
        )
        assert review_resp.status_code == 200
        assert review_resp.json()["status"] == "REJECTED"


