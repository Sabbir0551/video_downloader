import pytest
from httpx import AsyncClient, ASGITransport
from app.main import create_application
from app.platforms.registry import get_platform_registry

@pytest.fixture
def app():
    return create_application()

@pytest.mark.asyncio
async def test_platform_registry_loaded():
    registry = get_platform_registry()
    data = registry.data
    assert data.total_platforms == 100
    assert data.tiers_summary["supported"] > 30
    assert data.tiers_summary["unsupported_no_video"] > 20

    # Test false friend resolution
    # QQ should not have QQMusic
    qq = registry.get_by_id("qq")
    assert qq is not None
    assert "QQMusic" not in qq.extractor_keys
    assert qq.tier == "unsupported_no_video"

    # Kik should not have Kika
    kik = registry.get_by_id("kik")
    assert kik is not None
    assert "Kika" not in kik.extractor_keys
    assert kik.tier == "unsupported_no_video"

    # Moj should not have Mojevideo
    moj = registry.get_by_id("moj")
    assert moj is not None
    assert "Mojevideo" not in moj.extractor_keys
    assert moj.tier == "supported"

    # Koo should be defunct
    koo = registry.get_by_id("koo")
    assert koo is not None
    assert koo.tier == "defunct"

@pytest.mark.asyncio
async def test_platforms_api_endpoints(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # GET /api/v1/platforms
        resp = await client.get("/api/v1/platforms")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 100
        assert "platforms" in data
        assert len(data["platforms"]) == 100

        # Filter by tier
        resp_supported = await client.get("/api/v1/platforms?tier=supported")
        assert resp_supported.status_code == 200
        assert resp_supported.json()["total"] == 38

        # Detection test: YouTube
        detect_yt = await client.get("/api/v1/platforms/detect?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert detect_yt.status_code == 200
        yt_data = detect_yt.json()
        assert yt_data["detected"] is True
        assert yt_data["platform"]["id"] == "youtube"
        assert yt_data["allowed"] is True

        # Detection test: WhatsApp (unsupported)
        detect_wa = await client.get("/api/v1/platforms/detect?url=https://chat.whatsapp.com/invite123")
        assert detect_wa.status_code == 200
        wa_data = detect_wa.json()
        assert wa_data["detected"] is True
        assert wa_data["allowed"] is False
        assert wa_data["tier"] == "unsupported_no_video"

