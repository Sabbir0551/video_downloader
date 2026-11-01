import json
import logging
import os
import shutil
import subprocess
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("anystream.transcoder")


def probe_media(file_path: str) -> Dict[str, Any]:
    """
    Runs ffprobe to inspect container and stream metadata.
    Returns parsed dictionary of streams and format info.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Media file not found: {file_path}")

    ffprobe_bin = shutil.which("ffprobe") or "ffprobe"
    cmd = [
        ffprobe_bin,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path,
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
        return json.loads(proc.stdout)
    except subprocess.CalledProcessError as e:
        logger.error("ffprobe failed on %s: %s", file_path, e.stderr)
        raise RuntimeError(f"ffprobe failed: {e.stderr.strip() or 'Unknown error'}") from e
    except Exception as e:
        logger.error("Unexpected error probing %s: %s", file_path, str(e))
        raise RuntimeError(f"Unable to probe media file: {str(e)}") from e


def verify_media_integrity(
    file_path: str,
    expect_video: bool = True,
    expect_audio: bool = True,
    min_duration: float = 0.5,
) -> Tuple[bool, Optional[str]]:
    """
    Validates output file integrity before completing the job:
    - Verifies file exists and has non-zero size.
    - Probes duration and ensures stream validity.
    - Checks for video stream (resolution > 0) if expect_video is True.
    - Checks for audio stream if expect_audio is True.
    Returns (is_valid, error_message).
    """
    if not os.path.exists(file_path):
        return False, "File does not exist on disk."

    size = os.path.getsize(file_path)
    if size < 1024:  # Under 1 KB is almost certainly corrupted or empty
        return False, f"File size too small ({size} bytes). Corrupt media artifact."

    try:
        probe = probe_media(file_path)
    except Exception as e:
        return False, f"Corrupted media header or unreadable streams: {str(e)}"

    fmt = probe.get("format", {})
    streams = probe.get("streams", [])

    duration_str = fmt.get("duration")
    try:
        duration = float(duration_str) if duration_str else 0.0
    except ValueError:
        duration = 0.0

    if duration < min_duration:
        return False, f"Invalid or truncated duration ({duration:.2f}s < {min_duration}s)."

    has_video = False
    has_audio = False

    for st in streams:
        codec_type = st.get("codec_type")
        if codec_type == "video":
            w = st.get("width") or 0
            h = st.get("height") or 0
            if w > 0 and h > 0:
                has_video = True
        elif codec_type == "audio":
            has_audio = True

    if expect_video and not has_video:
        return False, "Output file is missing a valid video stream."

    if expect_audio and not has_audio:
        return False, "Output file is missing a valid audio stream."

    return True, None


def convert_to_compatible_mp4(
    input_path: str,
    output_path: Optional[str] = None,
    crf: int = 22,
    audio_bitrate: str = "192k",
) -> str:
    """
    Ensures the media file is fully compatible across all devices:
    - Container: MP4
    - Video codec: H.264 (libx264)
    - Audio codec: AAC
    - Faststart enabled for web streaming (moov atom at front)
    
    If already H.264/AAC in MP4, executes instant lossless remux (-c copy).
    Otherwise executes optimized transcoding.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if not output_path:
        base, _ = os.path.splitext(input_path)
        output_path = f"{base}_compatible.mp4"

    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"

    # Inspect current codecs
    probe = probe_media(input_path)
    streams = probe.get("streams", [])

    video_codec = None
    audio_codec = None
    for st in streams:
        if st.get("codec_type") == "video" and not video_codec:
            video_codec = st.get("codec_name", "").lower()
        elif st.get("codec_type") == "audio" and not audio_codec:
            audio_codec = st.get("codec_name", "").lower()

    # Determine if lossless copy is possible
    can_copy_v = video_codec in ("h264", "avc1")
    can_copy_a = audio_codec in ("aac", "mp4a")

    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", input_path,
    ]

    if can_copy_v and can_copy_a:
        logger.info("Stream is already H.264/AAC. Performing lossless fast remux to MP4.")
        cmd.extend(["-c", "copy", "-movflags", "+faststart", output_path])
    else:
        logger.info("Transcoding to Compatible MP4 (Video: %s->h264, Audio: %s->aac)", video_codec, audio_codec)
        v_args = ["-c:v", "copy"] if can_copy_v else ["-c:v", "libx264", "-preset", "fast", "-crf", str(crf)]
        a_args = ["-c:a", "copy"] if can_copy_a else ["-c:a", "aac", "-b:a", audio_bitrate]
        cmd.extend(v_args)
        cmd.extend(a_args)
        cmd.extend(["-movflags", "+faststart", output_path])

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=300)
        logger.info("Compatible MP4 created successfully at %s", output_path)
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error("FFmpeg conversion failed: %s", e.stderr)
        raise RuntimeError(f"FFmpeg transcode failed: {e.stderr.strip()}") from e
