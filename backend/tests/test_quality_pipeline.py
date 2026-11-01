import os
import pytest
from app.services.extractor import normalize_formats
from app.services.transcoder import verify_media_integrity

def test_best_quality_pipeline_format_selection():
    """Verify that 4K/VP9/AV1 streams are kept as Original Best and Compatible MP4 is offered."""
    raw_formats = [
        # 4K VP9 stream (highest fidelity)
        {
            "format_id": "313",
            "ext": "webm",
            "height": 2160,
            "fps": 60,
            "vcodec": "vp09.00.51.08.01.01.01.01.00",
            "acodec": "none",
            "vbr": 18000.0,
            "tbr": 18000.0,
            "dynamic_range": "HDR10",
            "filesize": 400000000,
        },
        # 1080p H.264 stream (AVC1)
        {
            "format_id": "137",
            "ext": "mp4",
            "height": 1080,
            "fps": 60,
            "vcodec": "avc1.64002a",
            "acodec": "none",
            "vbr": 4500.0,
            "tbr": 4500.0,
            "dynamic_range": "SDR",
            "filesize": 95000000,
        },
        # 1080p VP9 stream (Higher bitrate than AVC1)
        {
            "format_id": "248",
            "ext": "webm",
            "height": 1080,
            "fps": 60,
            "vcodec": "vp09.00.41.08",
            "acodec": "none",
            "vbr": 6000.0,
            "tbr": 6000.0,
            "dynamic_range": "SDR",
            "filesize": 120000000,
        },
        # Best audio stream: Opus
        {
            "format_id": "251",
            "ext": "webm",
            "vcodec": "none",
            "acodec": "opus",
            "abr": 160.0,
            "filesize": 4000000,
        },
        # AAC audio stream
        {
            "format_id": "140",
            "ext": "m4a",
            "vcodec": "none",
            "acodec": "mp4a.40.2",
            "abr": 128.0,
            "filesize": 3200000,
        },
    ]

    formats = normalize_formats(raw_formats, duration=180)

    # 1. 4K stream must be present, marked is_best=True, and have HDR flag
    fmt_4k = next((f for f in formats if f.height == 2160 and f.mode == "original"), None)
    assert fmt_4k is not None
    assert fmt_4k.is_best is True
    assert fmt_4k.is_hdr is True
    assert "313+251" in fmt_4k.format_id
    assert "4K" in fmt_4k.format_note

    # 2. 1080p must have both Original Best (VP9) and Compatible MP4 (H.264)
    fmt_1080_orig = next((f for f in formats if f.height == 1080 and f.mode == "original"), None)
    assert fmt_1080_orig is not None
    assert "248+251" in fmt_1080_orig.format_id

    fmt_1080_compat = next((f for f in formats if f.height == 1080 and f.mode == "compatible_mp4"), None)
    assert fmt_1080_compat is not None
    assert "137" in fmt_1080_compat.format_id
    assert fmt_1080_compat.ext == "mp4"

    # 3. Audio options: Original + MP3 320 + MP3 192
    audio_orig = next((f for f in formats if f.is_audio_only and f.mode == "original"), None)
    assert audio_orig is not None
    assert audio_orig.format_id == "251"

    audio_mp3_320 = next((f for f in formats if f.is_audio_only and "+mp3_320" in f.format_id), None)
    assert audio_mp3_320 is not None
    assert audio_mp3_320.abr == 320.0

    audio_mp3_192 = next((f for f in formats if f.is_audio_only and f.format_id.endswith("+mp3")), None)
    assert audio_mp3_192 is not None


def test_integrity_check_detects_corrupt_file(tmp_path):
    """Verify verify_media_integrity identifies truncated / invalid media."""
    # Empty file
    empty_file = tmp_path / "empty.mp4"
    empty_file.write_bytes(b"")
    is_valid, err = verify_media_integrity(str(empty_file))
    assert is_valid is False
    assert "too small" in err or "does not exist" in err

    # Truncated random noise
    noise_file = tmp_path / "noise.mp4"
    noise_file.write_bytes(b"NOT A REAL VIDEO FILE DATA" * 50)
    is_valid_noise, err_noise = verify_media_integrity(str(noise_file))
    assert is_valid_noise is False
