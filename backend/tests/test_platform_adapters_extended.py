import json
from unittest.mock import MagicMock, patch
import pytest

from app.platforms.adapters import (
    TelegramAdapter,
    XiaohongshuAdapter,
    SubstackAdapter,
    DirectEmbedAdapter,
    get_platform_adapter,
)
from app.services.embed_resolver import (
    is_direct_media_url,
    build_direct_media_info,
    extract_embed_or_media_from_html,
)


def test_telegram_adapter_canonicalize():
    adapter = TelegramAdapter()
    assert adapter.canonicalize_url("https://t.me/s/durov/123") == "https://t.me/durov/123"
    assert adapter.canonicalize_url("https://t.me/telegram_channel/456?single") == "https://t.me/telegram_channel/456"
    assert adapter.canonicalize_url("https://t.me/s/channel/789?test=1") == "https://t.me/channel/789"


def test_telegram_custom_media_mock():
    adapter = TelegramAdapter()
    sample_html = """
    <html>
      <head><title>Telegram Web</title></head>
      <body>
        <div class="tgme_widget_message_text">Breaking tech announcement video!</div>
        <video src="https://cdn4.telesco.pe/file/sample_video.mp4" class="tgme_widget_message_video"></video>
      </body>
    </html>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = sample_html

    with patch("httpx.Client.get", return_value=mock_resp):
        info = adapter.extract_custom_media("https://t.me/tech_news/101")
        assert info is not None
        assert info["id"] == "tg_tech_news_101"
        assert "Breaking tech announcement" in info["title"]
        assert info["formats"][0]["url"] == "https://cdn4.telesco.pe/file/sample_video.mp4"
        assert info["formats"][0]["ext"] == "mp4"


def test_xiaohongshu_adapter_canonicalize():
    adapter = XiaohongshuAdapter()
    url = "https://xiaohongshu.com/explore/64a1b2c3d4e5f6"
    canonical = adapter.canonicalize_url(url)
    assert canonical == "https://www.xiaohongshu.com/explore/64a1b2c3d4e5f6"


def test_xiaohongshu_custom_media_initial_state():
    adapter = XiaohongshuAdapter()
    mock_state = {
        "note": {
            "noteDetailMap": {
                "64a1b2c3": {
                    "note": {
                        "title": "Amazing Travel Vlog",
                        "video": {
                            "media": {
                                "stream": {
                                    "h264": [
                                        {"masterUrl": "https://sns-video-bd.xhscdn.com/stream/vlog1080p.mp4"}
                                    ]
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    sample_html = f"<html><body><script>window.__INITIAL_STATE__ = {json.dumps(mock_state)};</script></body></html>"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = sample_html

    with patch("httpx.Client.get", return_value=mock_resp):
        info = adapter.extract_custom_media("https://www.xiaohongshu.com/explore/64a1b2c3")
        assert info is not None
        assert info["title"] == "Amazing Travel Vlog"
        assert info["formats"][0]["url"] == "https://sns-video-bd.xhscdn.com/stream/vlog1080p.mp4"


def test_substack_adapter_canonicalize_and_audio():
    adapter = SubstackAdapter()
    url = "https://newsletter.substack.com/p/episode-42-ai-future?utm_source=twitter&utm_medium=post"
    canonical = adapter.canonicalize_url(url)
    assert canonical == "https://newsletter.substack.com/p/episode-42-ai-future"

    sample_html = """
    <html>
      <head><title>Substack Post</title></head>
      <body>
        <h1>Episode 42: The AI Future</h1>
        <audio src="https://bucketeer.s3.amazonaws.com/substack/episode42.mp3"></audio>
      </body>
    </html>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = sample_html

    with patch("httpx.Client.get", return_value=mock_resp):
        info = adapter.extract_custom_media("https://newsletter.substack.com/p/episode-42-ai-future")
        assert info is not None
        assert "Episode 42" in info["title"]
        assert info["formats"][0]["ext"] == "mp3"
        assert info["formats"][0]["url"] == "https://bucketeer.s3.amazonaws.com/substack/episode42.mp3"


def test_embed_resolver_direct_and_html():
    # Direct media URL check
    assert is_direct_media_url("https://cdn.discordapp.com/attachments/123/456/demo.mp4") is True
    assert is_direct_media_url("https://example.com/podcast.mp3") is True
    assert is_direct_media_url("https://example.com/page.html") is False

    direct_info = build_direct_media_info("https://example.com/assets/presentation.webm")
    assert direct_info["formats"][0]["ext"] == "webm"
    assert direct_info["formats"][0]["format_id"] == "direct"

    # HTML iframe resolution (e.g. Medium or Dev.to embedding YouTube)
    html_with_yt_iframe = """
    <html><body>
      <article>
        <h1>Cool Dev Article</h1>
        <iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ" width="560" height="315"></iframe>
      </article>
    </body></html>
    """
    res = extract_embed_or_media_from_html(html_with_yt_iframe, "https://dev.to/user/cool-post")
    assert res is not None
    assert res["type"] == "resolved_url"
    assert "youtube.com/embed/dQw4w9WgXcQ" in res["url"]

    # HTML OpenGraph resolution
    html_with_og = """
    <html><head>
      <meta property="og:video" content="https://example.com/videos/promo.mp4" />
    </head></html>
    """
    og_res = extract_embed_or_media_from_html(html_with_og, "https://behance.net/gallery/1234")
    assert og_res is not None
    assert og_res["url"] == "https://example.com/videos/promo.mp4"


def test_adapter_registry_lookup():
    assert get_platform_adapter("telegram").platform_id == "telegram"
    assert get_platform_adapter("xiaohongshu").platform_id == "xiaohongshu"
    assert get_platform_adapter("substack").platform_id == "substack"
    assert get_platform_adapter("github").platform_id == "embed_or_direct"
    assert get_platform_adapter("discord").platform_id == "embed_or_direct"

