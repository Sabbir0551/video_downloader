import glob
import json
import logging
import os
import shutil
import time
import uuid
from typing import Any, Dict, Optional

import redis
import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError

from app.core.config import settings
from app.core.security import generate_download_token, sanitize_filename
from app.core.ssrf import safe_network_guard
from app.db.session import get_sync_db
from app.models.job import DownloadJob, JobStatus
from app.services.extractor import SilentLogger, map_ytdlp_error
from app.services.storage import get_storage
from app.worker.celery_app import celery_app

logger = logging.getLogger("anystream.worker")

# Redis client for high-frequency progress publishing
try:
    redis_client = redis.Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=0.5,
        socket_timeout=0.5,
    )
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


@celery_app.task(
    bind=True,
    name="app.worker.tasks.download_media_task",
    acks_late=True,
    reject_on_worker_lost=True,
)
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
    - Idempotent: checks state before processing and before final completion.
    - Aborts immediately if job was cancelled.
    - Monitored for maximum file size and disk backpressure.
    """
    logger.info("Starting download task for Job [%s] - URL: %s - Format: %s", job_id, url, format_id)

    # 1. Ensure storage directory exists
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)

    # 2. Check disk backpressure quota
    try:
        free_bytes = shutil.disk_usage(settings.STORAGE_DIR).free
        if free_bytes < settings.MIN_FREE_DISK_BYTES:
            logger.error("Disk quota exceeded: only %d bytes free (min %d).", free_bytes, settings.MIN_FREE_DISK_BYTES)
            with get_sync_db() as db:
                job = db.get(DownloadJob, uuid.UUID(job_id))
                if job:
                    job.status = JobStatus.FAILED
                    job.error_code = "DISK_QUOTA_EXCEEDED"
                    job.error_message = "Server disk space is temporarily insufficient. Please try again shortly."
                    db.commit()
            return {"status": "FAILED", "error": "Insufficient server disk space"}
    except Exception as e:
        logger.warning("Could not check disk usage: %s", str(e))

    # 3. Read and verify job state before starting
    with get_sync_db() as db:
        job = db.get(DownloadJob, uuid.UUID(job_id))
        if not job:
            logger.error("Job [%s] not found in database.", job_id)
            return {"status": "FAILED", "error": "Job not found"}

        # If cancelled while queued, abort immediately
        if job.status == JobStatus.CANCELLED:
            logger.info("Job [%s] was cancelled before execution started. Aborting.", job_id)
            return {"status": "CANCELLED", "job_id": job_id}

        # Idempotency check: if already completed, return existing result
        if job.status == JobStatus.COMPLETED:
            logger.info("Job [%s] already marked COMPLETED. Returning idempotent cached state.", job_id)
            return {
                "job_id": job_id,
                "status": "COMPLETED",
                "progress": 100.0,
                "file_size": job.file_size,
                "download_url": job.download_url,
            }

        job.status = JobStatus.PROCESSING
        job.progress = 0.0
        db.commit()

    # 4. Build output template decoupled from video title
    # Format: /storage/tmp/{job_id}.%(ext)s
    output_template = os.path.join(settings.STORAGE_DIR, f"{job_id}.%(ext)s")

    # 5. Progress hook closure
    last_update_time = 0.0

    def progress_hook(d: Dict[str, Any]) -> None:
        nonlocal last_update_time
        now = time.time()

        # Enforce hard byte limit while downloading
        downloaded = d.get("downloaded_bytes", 0)
        if downloaded > settings.MAX_FILE_SIZE_BYTES:
            raise DownloadError(
                f"File size limit exceeded: downloaded {downloaded} bytes > maximum {settings.MAX_FILE_SIZE_BYTES} bytes allowed."
            )

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

    # 5. Build yt-dlp configuration with format_sort and platform adapter
    from app.platforms.adapters import get_platform_adapter
    from app.platforms.registry import get_platform_registry

    reg = get_platform_registry()
    matched_plat = reg.find_by_url(url)
    adapter = get_platform_adapter(matched_plat.id if matched_plat else None)
    target_url = adapter.canonicalize_url(url)

    needs_mp4_transcode = ":transcode_mp4" in format_id
    clean_format_id = format_id.replace(":transcode_mp4", "").replace("+mp3_320", "").replace("+mp3", "")
    is_mp3 = "+mp3" in format_id
    mp3_quality = "320" if "+mp3_320" in format_id else "192"

    if is_audio_only and clean_format_id in ["best", ""]:
        clean_format_id = "bestaudio/best"
    elif not is_audio_only and clean_format_id in ["best", ""]:
        clean_format_id = "bestvideo+bestaudio/best"

    ydl_opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "outtmpl": output_template,
        "format": clean_format_id,
        "format_sort": ["res", "fps", "hdr:12", "vcodec", "channels", "acodec", "size", "br"],
        "max_filesize": settings.MAX_FILE_SIZE_BYTES,
        "socket_timeout": 60,
        "retries": 10,
        "fragment_retries": 10,
        "noplaylist": True,
        "no_color": True,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "progress_hooks": [progress_hook],
        "logger": SilentLogger(),
        "js_runtimes": {"node": {}},
    }

    adapter_opts = adapter.get_ydl_options(target_url)
    if adapter_opts:
        ydl_opts.update(adapter_opts)

    # Audio extraction postprocessor
    if is_audio_only:
        ydl_opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3" if is_mp3 else "m4a",
                "preferredquality": mp3_quality if is_mp3 else "192",
            }
        ]
    else:
        if needs_mp4_transcode:
            ydl_opts["merge_output_format"] = "mp4"
        else:
            ydl_opts["merge_output_format"] = "mkv"

    # 6. Execute extraction and download
    try:
        with safe_network_guard():
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([target_url])
            except Exception as dl_err:
                logger.info("Direct yt-dlp download failed for %s, trying adapter custom media: %s", target_url, str(dl_err))
                custom_res = adapter.extract_custom_media(target_url)
                if custom_res and "formats" in custom_res:
                    direct_stream_url = custom_res["formats"][0].get("url")
                    if direct_stream_url:
                        ydl_opts["format"] = "best"
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([direct_stream_url])
                    else:
                        raise dl_err
                elif custom_res and custom_res.get("type") == "resolved_url":
                    resolved_url = custom_res["url"]
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([resolved_url])
                else:
                    raise dl_err

        # Locate finalized file on disk
        matching_files = glob.glob(os.path.join(settings.STORAGE_DIR, f"{job_id}.*"))
        valid_files = [f for f in matching_files if not f.endswith((".part", ".ytdl", ".temp"))]

        if not valid_files:
            raise DownloadError("Finalized media file was not created on disk.")

        final_path = valid_files[0]

        # If compatible MP4 requested, transcode or remux
        if needs_mp4_transcode and not is_audio_only:
            try:
                from app.services.transcoder import convert_to_compatible_mp4
                compat_path = os.path.join(settings.STORAGE_DIR, f"{job_id}_compat.mp4")
                convert_to_compatible_mp4(final_path, compat_path)
                try:
                    os.remove(final_path)
                except OSError:
                    pass
                final_path = compat_path
            except Exception as trans_err:
                logger.warning("Compatible MP4 transcode failed (%s). Retaining original container.", str(trans_err))

        # Media integrity verification via ffprobe
        from app.services.transcoder import verify_media_integrity
        is_valid, integrity_err = verify_media_integrity(
            final_path,
            expect_video=not is_audio_only,
            expect_audio=True,
        )
        if not is_valid:
            logger.warning("Integrity check warning for Job [%s]: %s", job_id, integrity_err)

        actual_size = os.path.getsize(final_path)
        file_ext = os.path.splitext(final_path)[1].lstrip(".")

        # Upload file to storage backend using random ID key (never video title)
        storage = get_storage()
        object_key = f"{job_id}.{file_ext}"
        try:
            storage_path = storage.upload(final_path, object_key)
            # If R2 storage, delete local temporary file and store only object key in job record
            if settings.STORAGE_BACKEND.lower() == "r2":
                try:
                    os.remove(final_path)
                except OSError:
                    pass
                stored_file_path = object_key
            else:
                stored_file_path = storage_path
        except Exception as upload_err:
            if settings.STORAGE_BACKEND.lower() == "r2":
                logger.warning(
                    "R2 storage upload failed (%s). Gracefully falling back to LocalStorage for Job [%s].",
                    str(upload_err),
                    job_id,
                )
                from app.services.storage import LocalStorage
                local_storage = LocalStorage()
                stored_file_path = local_storage.upload(final_path, object_key)
            else:
                raise

        # Generate signed expiring download token
        with get_sync_db() as db:
            job = db.get(DownloadJob, uuid.UUID(job_id))
            if not job or job.status == JobStatus.CANCELLED:
                logger.info("Job [%s] was cancelled during processing. Purging artifacts.", job_id)
                storage.delete(stored_file_path)
                return {"status": "CANCELLED", "job_id": job_id}

            safe_display_name = sanitize_filename(job.title or "media_download", file_ext)
            token = generate_download_token(
                job_id=job_id,
                file_name=safe_display_name,
                expiry_seconds=settings.JOB_EXPIRY_MINUTES * 60,
            )

            download_url = f"/api/v1/downloads/{job_id}/file?token={token}"
            job.status = JobStatus.COMPLETED
            job.progress = 100.0
            job.file_path = stored_file_path
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

        is_cancelled = False
        with get_sync_db() as db:
            job = db.get(DownloadJob, uuid.UUID(job_id))
            if job:
                if job.status == JobStatus.CANCELLED:
                    is_cancelled = True
                else:
                    job.status = JobStatus.FAILED
                    job.error_code = app_err.error_code
                    job.error_message = app_err.message
                    db.commit()

        if is_cancelled:
            return {"status": "CANCELLED", "job_id": job_id}

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

    storage = get_storage()
    with get_sync_db() as db:
        # Find jobs past their expiration timestamp that are not yet marked EXPIRED
        expired_stmt = select(DownloadJob).where(
            DownloadJob.expires_at <= now,
            DownloadJob.status != JobStatus.EXPIRED,
        )
        expired_jobs = db.execute(expired_stmt).scalars().all()

        for job in expired_jobs:
            # Delete file in storage backend if exists
            if job.file_path:
                try:
                    storage.delete(job.file_path)
                    evicted_files += 1
                except Exception as e:
                    logger.warning("Error deleting expired file %s from storage: %s", job.file_path, str(e))

            # Delete any leftover partial fragments for this job_id on local disk
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


@celery_app.task(name="app.worker.tasks.check_ytdlp_version_task")
def check_ytdlp_version_task() -> Dict[str, Any]:
    """Periodic task checking PyPI for newer versions of yt-dlp to anticipate extractor breakages."""
    current_ver = getattr(yt_dlp.version, "__version__", "unknown")
    latest_ver = current_ver
    try:
        import urllib.request
        with urllib.request.urlopen("https://pypi.org/pypi/yt-dlp/json", timeout=5.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                latest_ver = data.get("info", {}).get("version", current_ver)
                if redis_client:
                    redis_client.set("ytdlp:latest_version", latest_ver)
                if latest_ver != current_ver:
                    logger.warning("yt-dlp update available: current=%s, latest=%s", current_ver, latest_ver)
    except Exception as e:
        logger.debug("yt-dlp version check skipped: %s", str(e))

    return {"current": current_ver, "latest": latest_ver}


