import asyncio
import hashlib
import json
import os
import urllib.parse
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import redis
from fastapi import APIRouter, Depends, Header, Query, Request, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import (
    AppError,
    ContentBlockedLegalError,
    DownloadTokenInvalidError,
    DRMProtectedError,
    GlobalConcurrencyExceededError,
    JobNotFoundError,
    MediaTooLargeError,
    RateLimitExceededError,
)
from app.core.rate_limit import (
    check_rate_limit,
    get_client_ip_hash,
)
from app.core.security import sanitize_filename, verify_download_token
from app.core.ssrf import validate_url_security
from app.db.session import get_db
from app.models.job import DownloadJob, JobStatus
from app.models.takedown import TakedownRecord, TakedownStatus
from app.schemas.common import ErrorResponse
from app.schemas.job import CreateJobRequest, JobStatusResponse
from app.services.extractor import extract_media_info
from app.services.storage import get_storage
from app.worker.celery_app import celery_app
from app.worker.tasks import download_media_task

router = APIRouter()

# Redis client for retrieving live progress
try:
    redis_client = redis.Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=0.5,
        socket_timeout=0.5,
    )
except Exception:
    redis_client = None


@router.post(
    "/downloads",
    response_model=JobStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create media download job",
    description="Validates URL, checks quotas, enqueues background download task in Celery, and returns initial job status.",
    responses={
        202: {
            "model": JobStatusResponse,
            "description": "Job accepted and enqueued in worker pool",
            "content": {
                "application/json": {
                    "example": {
                        "job_id": "550e8400-e29b-41d4-a716-446655440000",
                        "status": "QUEUED",
                        "progress": 0.0,
                        "speed": None,
                        "eta": None,
                        "file_size": None,
                        "download_url": None,
                        "created_at": "2026-10-30T02:00:00Z",
                        "expires_at": "2026-10-30T02:30:00Z",
                        "error_code": None,
                        "error_message": None,
                    }
                }
            },
        },
        400: {
            "model": ErrorResponse,
            "description": "SSRF violation or invalid parameters",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "SSRF_DESTINATION_FORBIDDEN",
                        "message": "Access to host '127.0.0.1' is denied by security policy.",
                        "details": {"hostname": "127.0.0.1"},
                    }
                }
            },
        },
        403: {
            "model": ErrorResponse,
            "description": "DRM-protected media",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "MEDIA_DRM_PROTECTED",
                        "message": "This media stream is DRM-protected and cannot be downloaded.",
                        "details": {},
                    }
                }
            },
        },
        429: {
            "model": ErrorResponse,
            "description": "Rate limit exceeded or IP active concurrency cap reached",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "message": "You already have maximum concurrent downloads in progress. Please wait for them to finish.",
                        "details": {"max_concurrent_jobs": 2},
                    }
                }
            },
        },
        451: {
            "model": ErrorResponse,
            "description": "Content unavailable due to legal or DMCA takedown",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "LEGAL_TAKEDOWN_BLOCK",
                        "message": "This content has been blocked due to a copyright or legal notice.",
                        "details": {},
                    }
                }
            },
        },
        503: {
            "model": ErrorResponse,
            "description": "Global server concurrency cap reached",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "GLOBAL_CONCURRENCY_EXCEEDED",
                        "message": "System download capacity is currently full. Please try again shortly.",
                        "details": {"global_concurrency_cap": 20},
                    }
                }
            },
        },
    },
)
async def create_download_job(
    request: Request,
    payload: CreateJobRequest,
    db: AsyncSession = Depends(get_db),
) -> JobStatusResponse:
    """Submits a new background media download job."""
    # 1. Hashed client IP (never stores raw IP) & Rate Limit Check (5 req/min)
    ip_hash = get_client_ip_hash(request)
    check_rate_limit(ip_hash, "downloads", settings.RATE_LIMIT_JOB_PER_MINUTE)

    # 2. SSRF Pre-Resolution Guard
    clean_url, _ = validate_url_security(payload.url)

    # 3. Check for active legal takedown / blacklist blocks
    url_hash = hashlib.sha256(clean_url.encode("utf-8")).hexdigest()
    takedown_stmt = select(TakedownRecord).where(
        TakedownRecord.url_hash == url_hash,
        TakedownRecord.status != TakedownStatus.REJECTED,
    )
    takedown_res = await db.execute(takedown_stmt)
    if takedown_res.scalars().first():
        raise ContentBlockedLegalError("This content has been blocked due to a copyright or legal notice.")

    # 4. Check Global Concurrency Cap (system-wide active downloads)
    global_active_stmt = select(func.count(DownloadJob.id)).where(
        DownloadJob.status.in_([JobStatus.QUEUED, JobStatus.PROCESSING])
    )
    global_active = (await db.execute(global_active_stmt)).scalar() or 0
    if global_active >= settings.GLOBAL_CONCURRENCY_CAP:
        raise GlobalConcurrencyExceededError()

    # 5. Check Per-IP Concurrency Cap (max 2 active jobs per IP hash)
    active_jobs_stmt = select(func.count(DownloadJob.id)).where(
        DownloadJob.ip_hash == ip_hash,
        DownloadJob.status.in_([JobStatus.QUEUED, JobStatus.PROCESSING]),
    )
    active_count = (await db.execute(active_jobs_stmt)).scalar() or 0
    if active_count >= settings.MAX_CONCURRENT_JOBS_PER_IP:
        raise RateLimitExceededError(
            "You already have maximum concurrent downloads in progress. Please wait for them to finish.",
            details={"max_concurrent_jobs": settings.MAX_CONCURRENT_JOBS_PER_IP},
        )

    # 6. Quick metadata extraction to verify duration limits & title
    media_info = await asyncio.to_thread(extract_media_info, clean_url)
    if media_info.duration > settings.MAX_VIDEO_DURATION_SECONDS:
        raise MediaTooLargeError(
            f"Video duration ({media_info.duration // 60}m) exceeds platform maximum of {settings.MAX_VIDEO_DURATION_SECONDS // 60}m."
        )

    # 7. Create database record
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.JOB_EXPIRY_MINUTES)
    job_id = uuid.uuid4()

    new_job = DownloadJob(
        id=job_id,
        url_hash=url_hash,
        original_url=clean_url,
        title=media_info.title,
        format_id=payload.format_id,
        quality_label=payload.quality_label,
        is_audio_only=payload.audio_only,
        status=JobStatus.QUEUED,
        progress=0.0,
        ip_hash=ip_hash,
        expires_at=expires_at,
    )

    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)

    # 8. Dispatch background worker task via Celery
    try:
        download_media_task.delay(
            job_id=str(new_job.id),
            url=clean_url,
            format_id=payload.format_id,
            is_audio_only=payload.audio_only,
            title=media_info.title,
        )
    except Exception:
        new_job.status = JobStatus.FAILED
        new_job.error_code = "TASK_QUEUE_UNAVAILABLE"
        new_job.error_message = "Background worker queue is currently offline. Please try again shortly."
        await db.commit()
        await db.refresh(new_job)

    return JobStatusResponse(
        job_id=new_job.id,
        status=new_job.status,
        progress=new_job.progress,
        speed=new_job.speed,
        eta=new_job.eta,
        file_size=new_job.file_size,
        download_url=new_job.download_url,
        created_at=new_job.created_at,
        expires_at=new_job.expires_at,
        error_code=new_job.error_code,
        error_message=new_job.error_message,
    )


@router.get(
    "/downloads/{job_id}/file",
    summary="Download finalized media file",
    description="Serves media file using a signed, expiring token. Supports HTTP Range requests.",
    responses={
        200: {
            "description": "Full media file stream",
            "content": {"application/octet-stream": {}},
        },
        206: {
            "description": "Partial content chunk (HTTP Range request)",
            "content": {"application/octet-stream": {}},
        },
        403: {
            "model": ErrorResponse,
            "description": "Invalid, tampered, or expired download token",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "DOWNLOAD_TOKEN_INVALID",
                        "message": "Download token has expired or signature is invalid.",
                        "details": {},
                    }
                }
            },
        },
        404: {
            "model": ErrorResponse,
            "description": "File expired or removed from storage",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "JOB_NOT_FOUND",
                        "message": "The requested file has expired or was pruned by the cleanup janitor.",
                        "details": {},
                    }
                }
            },
        },
    },
)
async def download_file(
    job_id: uuid.UUID,
    token: Annotated[str, Query(description="Cryptographically signed expiring download token")],
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Serves media file with signed token validation and safe Content-Disposition headers."""
    # 1. Validate cryptographic token integrity and expiration
    payload = verify_download_token(token)
    if payload.get("job_id") != str(job_id):
        raise DownloadTokenInvalidError("Token does not correspond to the requested job ID.")

    # 2. Check job record
    stmt = select(DownloadJob).where(DownloadJob.id == job_id)
    res = await db.execute(stmt)
    job = res.scalars().first()

    if not job or job.status != JobStatus.COMPLETED or not job.file_path:
        raise JobNotFoundError("The requested file has expired or was pruned by the cleanup janitor.")

    # 3. Check storage backend for file existence
    storage = get_storage()
    if not storage.exists(job.file_path):
        raise JobNotFoundError("The requested file has expired or was pruned by the cleanup janitor.")

    # 4. Construct RFC 5987 / RFC 6266 safe filename (Strict ASCII in filename, UTF-8 in filename*)
    file_ext = job.file_ext or os.path.splitext(job.file_path)[1].lstrip(".") or "mp4"
    safe_filename = sanitize_filename(job.title or "media_download", file_ext)

    # If storage backend supports direct presigned URL (e.g. Cloudflare R2), redirect client
    presigned_url = storage.get_presigned_url(
        object_key=job.file_path,
        filename=safe_filename,
        expiry_seconds=settings.JOB_EXPIRY_MINUTES * 60,
    )
    if presigned_url:
        return RedirectResponse(
            url=presigned_url,
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )

    # LocalStorage: serve directly with FileResponse
    encoded_filename = urllib.parse.quote(safe_filename)
    ascii_clean = safe_filename.encode("ascii", "ignore").decode("ascii").strip(" ._")
    base_ascii = os.path.splitext(ascii_clean)[0].strip(" ._") if ascii_clean else ""
    ascii_filename = f"{base_ascii}.{file_ext}" if base_ascii else f"video_download.{file_ext}"

    # Determine media mime type
    media_type = "video/mp4"
    if file_ext == "mp3":
        media_type = "audio/mpeg"
    elif file_ext == "m4a":
        media_type = "audio/mp4"
    elif file_ext == "webm":
        media_type = "video/webm"

    content_disposition = (
        f'attachment; filename="{ascii_filename}"; filename*=UTF-8\'\'{encoded_filename}'
    )

    return FileResponse(
        path=job.file_path,
        media_type=media_type,
        headers={"Content-Disposition": content_disposition},
    )


@router.delete(
    "/downloads/{job_id}",
    response_model=JobStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel running job and delete files",
    description="Terminates worker task execution and purges partial disk fragments.",
    responses={
        200: {"model": JobStatusResponse, "description": "Job cancelled successfully"},
        404: {"model": ErrorResponse, "description": "Job not found"},
    },
)
async def cancel_download_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> JobStatusResponse:
    """Cancels a queued or active job and evicts any partial files."""
    import glob

    stmt = select(DownloadJob).where(DownloadJob.id == job_id)
    res = await db.execute(stmt)
    job = res.scalars().first()

    if not job:
        raise JobNotFoundError("Download job not found.")

    # Revoke Celery task if queued/processing
    if job.status in [JobStatus.QUEUED, JobStatus.PROCESSING]:
        try:
            celery_app.control.revoke(str(job_id), terminate=True, signal="SIGTERM")
        except Exception:
            pass

    # Delete storage file if exists
    storage = get_storage()
    if job.file_path:
        try:
            storage.delete(job.file_path)
        except Exception:
            pass

    # Delete any partial fragments matching {job_id}*
    for partial_file in glob.glob(os.path.join(settings.STORAGE_DIR, f"{job_id}*")):
        try:
            os.remove(partial_file)
        except OSError:
            pass

    job.status = JobStatus.CANCELLED
    job.error_code = "USER_CANCELLED"
    job.error_message = "The download job was cancelled by the user."
    await db.commit()
    await db.refresh(job)

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        speed=job.speed,
        eta=job.eta,
        file_size=job.file_size,
        download_url=None,
        created_at=job.created_at,
        expires_at=job.expires_at,
        error_code=job.error_code,
        error_message=job.error_message,
    )


@router.get(
    "/downloads/{job_id:path}",
    response_model=JobStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get download job status and progress",
    description="Returns current status, progress percentage, ETA, and download URL when completed. Accepts job UUID or video URL.",
    responses={
        200: {"model": JobStatusResponse, "description": "Current job status"},
        404: {
            "model": ErrorResponse,
            "description": "Job not found or expired",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "JOB_NOT_FOUND",
                        "message": "Download job not found or has expired.",
                        "details": {},
                    }
                }
            },
        },
    },
)
async def get_download_status(
    job_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JobStatusResponse:
    """Retrieves real-time job state and metrics. Accepts UUID or media URL."""
    clean_id_str = urllib.parse.unquote(str(job_id)).strip()
    job = None

    # 1. If user entered a video URL instead of a UUID, look up or auto-enqueue
    if clean_id_str.startswith(("http://", "https://")):
        clean_url, _ = validate_url_security(clean_id_str)
        url_hash = hashlib.sha256(clean_url.encode("utf-8")).hexdigest()
        stmt = (
            select(DownloadJob)
            .where(DownloadJob.url_hash == url_hash)
            .order_by(DownloadJob.created_at.desc())
        )
        res = await db.execute(stmt)
        job = res.scalars().first()

        # If no job exists yet for this URL, auto-enqueue it!
        if not job:
            return await create_download_job(request, CreateJobRequest(url=clean_url), db)
    else:
        try:
            target_uuid = uuid.UUID(clean_id_str)
        except ValueError:
            raise JobNotFoundError("Invalid job ID or video URL format.")

        stmt = select(DownloadJob).where(DownloadJob.id == target_uuid)
        res = await db.execute(stmt)
        job = res.scalars().first()

    if not job:
        raise JobNotFoundError("Download job not found or has expired. Please submit the URL to start a new download.")

    # Live progress overlay from Redis if job is processing
    progress = job.progress
    speed = job.speed
    eta = job.eta

    if job.status == JobStatus.PROCESSING and redis_client:
        try:
            cached_progress_str = redis_client.get(f"job:{job.id}:progress")
            if cached_progress_str:
                cached_data = json.loads(cached_progress_str)
                progress = float(cached_data.get("progress") or progress)
                speed = cached_data.get("speed") or speed
                eta_val = cached_data.get("eta")
                if eta_val is not None:
                    try:
                        eta = int(round(float(eta_val)))
                    except (ValueError, TypeError):
                        eta = None
                else:
                    eta = job.eta
        except Exception:
            pass

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        progress=progress,
        speed=speed,
        eta=eta,
        file_size=job.file_size,
        download_url=job.download_url,
        created_at=job.created_at,
        expires_at=job.expires_at,
        error_code=job.error_code,
        error_message=job.error_message,
    )


# Alias endpoint /jobs to maintain full OpenAPI backwards compatibility
@router.post(
    "/jobs",
    response_model=JobStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
)
async def create_job_alias(
    request: Request,
    payload: CreateJobRequest,
    db: AsyncSession = Depends(get_db),
) -> JobStatusResponse:
    return await create_download_job(request, payload, db)
