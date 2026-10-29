import glob
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, Optional

import redis
import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError

from app.core.config import settings
from app.core.security import generate_download_token, sanitize_filename
from app.db.session import get_sync_db
from app.models.job import DownloadJob, JobStatus
from app.services.extractor import SilentLogger, map_ytdlp_error
from app.worker.celery_app import celery_app

logger = logging.getLogger("anystream.worker")

# Redis client for high-frequency progress publishing
try:
    redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception as e:
    redis_client = None
    logger.warning("Redis client initialization deferred: %s", str(e))


def update_progress_in_redis(job_id: str, payload: Dict[str, Any]) -> None:
    """Publishes download progress to Redis for SSE and polling consumers."""
    if not redis_client:
        return
    try:
        redis_key = f"job:{job_id}:progress"
        redis_client.setex(redis_key, 1800, json.dumps(payload))
        redis_client.publish(f"channel:job:{job_id}", json.dumps(payload))
    except Exception as err:
        logger.debug("Could not publish progress to Redis: %s", str(err))


@celery_app.task(bind=True, name="app.worker.tasks.download_media_task")
def download_media_task(
    self,
    job_id: str,
    url: str,
    format_id: str,
    is_audio_only: bool = False,
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes asynchronous media download and FFmpeg merging in sandboxed worker.
    - Files are saved strictly under random UUID paths in temporary storage.
    - User input is never used as a filesystem path.
    - Progress is reported to Redis in real time.
    """
    logger.info("Starting download task for Job [%s] - URL: %s - Format: %s", job_id, url, format_id)

    # 1. Ensure storage directory exists
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)

    # 2. Update status to PROCESSING in database
    with get_sync_db() as db:
        job = db.get(DownloadJob, uuid.UUID(job_id))
        if not job:
            logger.error("Job [%s] not found in database.", job_id)
            return {"status": "FAILED", "error": "Job not found"}
        job.status = JobStatus.PROCESSING
        job.progress = 0.0
        db.commit()

    # 3. Build output template decoupled from video title
    # Format: /storage/tmp/{job_id}.%(ext)s
    output_template = os.path.join(settings.STORAGE_DIR, f"{job_id}.%(ext)s")

    # 4. Progress hook closure
    last_update_time = 0.0

    def progress_hook(d: Dict[str, Any]) -> None:
        nonlocal last_update_time
        now = time.time()
        # Rate limit progress events to at most once every 0.5s to conserve I/O
        if now - last_update_time < 0.5 and d.get("status") == "downloading":
            return

        if d.get("status") == "downloading":
            downloaded = d.get("downloaded_bytes", 0)
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            percentage = round((downloaded / total) * 100.0, 1) if total > 0 else 0.0

            speed_bytes = d.get("speed") or 0
            if speed_bytes > 1024 * 1024:
                speed_str = f"{speed_bytes / (1024 * 1024):.1f} MB/s"
            elif speed_bytes > 1024:
                speed_str = f"{speed_bytes / 1024:.1f} KB/s"
            else:
                speed_str = f"{speed_bytes} B/s"

            eta_sec = None
            if d.get("eta") is not None:
                try:
                    eta_sec = int(round(float(d["eta"])))
                except (ValueError, TypeError):
                    eta_sec = None

            progress_data = {
                "job_id": job_id,
                "status": "PROCESSING",
                "progress": percentage,
                "speed": speed_str,
                "eta": eta_sec,
            }
            update_progress_in_redis(job_id, progress_data)
            last_update_time = now

    # 5. Build yt-dlp configuration
    clean_format_id = format_id.replace("+mp3", "")
    if is_audio_only and clean_format_id in ["best", ""]:
        clean_format_id = "bestaudio/best"
    elif not is_audio_only and clean_format_id in ["best", ""]:
        clean_format_id = "bestvideo+bestaudio/best"
    ydl_opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "outtmpl": output_template,
        "format": clean_format_id,
        "max_filesize": settings.MAX_FILE_SIZE_BYTES,
        "socket_timeout": 30,
        "noplaylist": True,
        "no_color": True,
        "progress_hooks": [progress_hook],
        "logger": SilentLogger(),
        "js_runtimes": {"node": {}},
    }

    # Audio extraction postprocessor
    if is_audio_only:
        target_audio_codec = "mp3" if "+mp3" in format_id else "m4a"
        ydl_opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": target_audio_codec,
                "preferredquality": "192",
            }
        ]
    else:
        # Merge video and audio into universal MP4 container
        ydl_opts["merge_output_format"] = "mp4"

    # 6. Execute extraction and download
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Locate finalized file on disk
        matching_files = glob.glob(os.path.join(settings.STORAGE_DIR, f"{job_id}.*"))
        # Filter out temporary/part files
        valid_files = [f for f in matching_files if not f.endswith((".part", ".ytdl", ".temp"))]

        if not valid_files:
            raise DownloadError("Finalized media file was not created on disk.")

        final_path = valid_files[0]
        actual_size = os.path.getsize(final_path)
        file_ext = os.path.splitext(final_path)[1].lstrip(".")

        # Generate signed expiring download token
        with get_sync_db() as db:
            job = db.get(DownloadJob, uuid.UUID(job_id))
            safe_display_name = sanitize_filename(job.title or "media_download", file_ext)
            token = generate_download_token(
                job_id=job_id,
                file_name=safe_display_name,
                expiry_seconds=settings.JOB_EXPIRY_MINUTES * 60,
            )

            download_url = f"/api/v1/downloads/{job_id}/file?token={token}"
            job.status = JobStatus.COMPLETED
            job.progress = 100.0
            job.file_path = final_path
            job.file_size = actual_size
            job.file_ext = file_ext
            job.download_url = download_url
            db.commit()

        completion_data = {
            "job_id": job_id,
            "status": "COMPLETED",
            "progress": 100.0,
            "file_size": actual_size,
            "download_url": download_url,
        }
        update_progress_in_redis(job_id, completion_data)
        logger.info("Download completed successfully for Job [%s] - Size: %d bytes", job_id, actual_size)
        return completion_data

    except Exception as err:
        logger.error("Download execution failed for Job [%s]: %s", job_id, str(err))
        app_err = map_ytdlp_error(err)

        # Clean up partial fragments
        for partial_file in glob.glob(os.path.join(settings.STORAGE_DIR, f"{job_id}*")):
            try:
                os.remove(partial_file)
            except OSError:
                pass

        with get_sync_db() as db:
            job = db.get(DownloadJob, uuid.UUID(job_id))
            if job:
                job.status = JobStatus.FAILED
                job.error_code = app_err.error_code
                job.error_message = app_err.message
                db.commit()

        failure_data = {
            "job_id": job_id,
            "status": "FAILED",
            "error_code": app_err.error_code,
            "error_message": app_err.message,
        }
        update_progress_in_redis(job_id, failure_data)
        return failure_data


@celery_app.task(name="app.worker.tasks.clean_expired_downloads_task")
def clean_expired_downloads_task() -> Dict[str, Any]:
    """
    Periodic Celery Beat janitor task running every 5 minutes.
    - Evicts physical files for jobs past expires_at (30 minutes).
    - Deletes failed or cancelled download fragments.
    - Marks database job status as EXPIRED.
    """
    from datetime import datetime, timezone
    from sqlalchemy import select

    now = datetime.now(timezone.utc)
    evicted_files = 0
    expired_jobs_count = 0

    with get_sync_db() as db:
        # Find jobs past their expiration timestamp that are not yet marked EXPIRED
        expired_stmt = select(DownloadJob).where(
            DownloadJob.expires_at <= now,
            DownloadJob.status != JobStatus.EXPIRED,
        )
        expired_jobs = db.execute(expired_stmt).scalars().all()

        for job in expired_jobs:
            # Delete file on disk if exists
            if job.file_path and os.path.exists(job.file_path):
                try:
                    os.remove(job.file_path)
                    evicted_files += 1
                except OSError as e:
                    logger.warning("Error deleting expired file %s: %s", job.file_path, str(e))

            # Delete any leftover partial fragments for this job_id
            for partial in glob.glob(os.path.join(settings.STORAGE_DIR, f"{job.id}*")):
                try:
                    os.remove(partial)
                    evicted_files += 1
                except OSError:
                    pass

            job.status = JobStatus.EXPIRED
            expired_jobs_count += 1

        db.commit()

    # Clean orphaned files on disk older than 35 minutes
    cutoff_time = time.time() - (35 * 60)
    for disk_file in glob.glob(os.path.join(settings.STORAGE_DIR, "*")):
        if os.path.isfile(disk_file):
            try:
                if os.path.getmtime(disk_file) < cutoff_time:
                    os.remove(disk_file)
                    evicted_files += 1
            except OSError:
                pass

    logger.info("Celery Beat Janitor: %d files evicted, %d jobs transitioned to EXPIRED.", evicted_files, expired_jobs_count)
    return {"evicted_files": evicted_files, "expired_jobs": expired_jobs_count}

