import asyncio
import hashlib
import json
import os
import shutil
import urllib.parse
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import redis
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Header, Query, Request, status
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from sqlalchemy import func, or_, select
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
    get_raw_client_ip,
)
from app.core.security import (
    generate_download_token,
    generate_job_access_token,
    normalize_video_url,
    sanitize_filename,
    verify_download_token,
    verify_job_access_token,
    verify_turnstile_captcha,
)
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

    # 2. CAPTCHA verification if required
    raw_ip = get_raw_client_ip(request)
    if settings.CLOUDFLARE_TURNSTILE_SECRET_KEY or payload.captcha_token:
        captcha_valid = await verify_turnstile_captcha(payload.captcha_token, raw_ip)
        if not captcha_valid:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="CAPTCHA_VERIFICATION_FAILED",
                message="Cloudflare Turnstile CAPTCHA verification failed. Please try again.",
            )

    # 3. Disk quota backpressure check
    try:
        free_bytes = shutil.disk_usage(settings.STORAGE_DIR).free
        if free_bytes < settings.MIN_FREE_DISK_BYTES:
            raise AppError(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                error_code="STORAGE_CAPACITY_FULL",
                message="Server storage capacity is currently constrained. Please try again shortly.",
            )
    except AppError:
        raise
    except Exception:
        pass

    # 4. SSRF Pre-Resolution Guard
    clean_url, _ = validate_url_security(payload.url)

    # 5. Check for active legal takedown / blacklist blocks (canonicalized)
    canonical_url, canonical_id = normalize_video_url(clean_url)
    raw_url_hash = hashlib.sha256(clean_url.encode("utf-8")).hexdigest()
    canon_url_hash = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()

    conds = [TakedownRecord.url_hash.in_([raw_url_hash, canon_url_hash])]
    if canonical_id:
        conds.append(TakedownRecord.channel_id == canonical_id)

    takedown_stmt = select(TakedownRecord).where(
        or_(*conds),
        TakedownRecord.status != TakedownStatus.REJECTED,
    )
    takedown_res = await db.execute(takedown_stmt)
    if takedown_res.scalars().first():
        raise ContentBlockedLegalError("This content has been blocked due to a copyright or legal notice.")

    # 6. Check Global Concurrency Cap (system-wide active downloads)
    global_active_stmt = select(func.count(DownloadJob.id)).where(
        DownloadJob.status.in_([JobStatus.QUEUED, JobStatus.PROCESSING])
    )
    global_active = (await db.execute(global_active_stmt)).scalar() or 0
    if global_active >= settings.GLOBAL_CONCURRENCY_CAP:
        raise GlobalConcurrencyExceededError()

    # 7. Check Per-IP Concurrency Cap (max 2 active jobs per IP hash)
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

    # 8. Quick metadata extraction to verify duration limits & title
    media_info = await asyncio.to_thread(extract_media_info, clean_url)
    if media_info.duration > settings.MAX_VIDEO_DURATION_SECONDS:
        raise MediaTooLargeError(
            f"Video duration ({media_info.duration // 60}m) exceeds platform maximum of {settings.MAX_VIDEO_DURATION_SECONDS // 60}m."
        )

    # 8b. Deduplication: return active job if identical download is already in progress
    dedup_stmt = (
        select(DownloadJob)
        .where(
            DownloadJob.url_hash.in_([raw_url_hash, canon_url_hash]),
            DownloadJob.format_id == payload.format_id,
            DownloadJob.status.in_([JobStatus.QUEUED, JobStatus.PROCESSING]),
        )
        .order_by(DownloadJob.created_at.desc())
    )
    existing_job = (await db.execute(dedup_stmt)).scalars().first()
    if existing_job:
        dedup_token = generate_job_access_token(str(existing_job.id))
        dedup_progress = existing_job.progress
        dedup_speed = existing_job.speed
        dedup_eta = existing_job.eta
        if redis_client:
            try:
                cached_p = redis_client.get(f"job:{existing_job.id}:progress")
                if cached_p:
                    p_dict = json.loads(cached_p)
                    dedup_progress = float(p_dict.get("progress", dedup_progress))
                    dedup_speed = p_dict.get("speed", dedup_speed)
                    dedup_eta = p_dict.get("eta", dedup_eta)
            except Exception:
                pass

        return JobStatusResponse(
            job_id=str(existing_job.id),
            status=existing_job.status.value,
            progress=dedup_progress,
            speed=dedup_speed,
            eta=dedup_eta,
            file_size=existing_job.file_size,
            download_url=existing_job.download_url,
            created_at=existing_job.created_at.isoformat(),
            expires_at=existing_job.expires_at.isoformat(),
            job_access_token=dedup_token,
        )

    # 9. Create database record
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.JOB_EXPIRY_MINUTES)
    job_id = uuid.uuid4()

    new_job = DownloadJob(
        id=job_id,
        url_hash=raw_url_hash,
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

    # 10. Dispatch background worker task via Celery with explicit task_id matching job_id
    try:
        download_media_task.apply_async(
            kwargs={
                "job_id": str(new_job.id),
                "url": clean_url,
                "format_id": payload.format_id,
                "is_audio_only": payload.audio_only,
                "title": media_info.title,
            },
            task_id=str(new_job.id),
        )
    except Exception:
        new_job.status = JobStatus.FAILED
        new_job.error_code = "TASK_QUEUE_UNAVAILABLE"
        new_job.error_message = "Background worker queue is currently offline. Please try again shortly."
        await db.commit()
        await db.refresh(new_job)

    job_access_token = generate_job_access_token(str(new_job.id))
    return JobStatusResponse(
        job_id=new_job.id,
        status=new_job.status,
        progress=new_job.progress,
        speed=new_job.speed,
        eta=new_job.eta,
        file_size=new_job.file_size,
        download_url=new_job.download_url,
        job_access_token=job_access_token,
        created_at=new_job.created_at,
        expires_at=new_job.expires_at,
        error_code=new_job.error_code,
        error_message=new_job.error_message,
    )


@router.api_route(
    "/downloads/{job_id}/file",
    methods=["GET", "HEAD"],
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

    # 3. Check storage backend or local filesystem for file existence
    file_ext = job.file_ext or os.path.splitext(job.file_path)[1].lstrip(".") or "mp4"
    safe_filename = sanitize_filename(job.title or "media_download", file_ext)

    presigned_url = None
    if os.path.isabs(job.file_path) and os.path.exists(job.file_path):
        pass
    else:
        storage = get_storage()
        if not storage.exists(job.file_path):
            raise JobNotFoundError("The requested file has expired or was pruned by the cleanup janitor.")

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


@router.get(
    "/downloads/{job_id}/stream",
    summary="Server-Sent Events (SSE) stream for download progress",
    description="Subscribes to Redis pub/sub channel for real-time progress events with keepalive.",
    responses={
        200: {
            "description": "SSE Event stream",
            "content": {"text/event-stream": {}},
        },
        404: {"model": ErrorResponse, "description": "Job not found"},
    },
)
async def stream_download_progress(
    job_id: str,
    request: Request,
    token: Optional[str] = Query(None),
    x_job_token: Optional[str] = Header(None, alias="X-Job-Token"),
    db: AsyncSession = Depends(get_db),
):
    """Streams real-time download progress events over SSE."""
    clean_id_str = urllib.parse.unquote(str(job_id)).strip()
    try:
        parsed_uuid = uuid.UUID(clean_id_str)
    except ValueError:
        raise JobNotFoundError("Invalid job UUID format.")

    stmt = select(DownloadJob).where(DownloadJob.id == parsed_uuid)
    res = await db.execute(stmt)
    job = res.scalars().first()

    if not job:
        raise JobNotFoundError("Job not found or has expired.")

    # Access token validation if supplied
    provided_token = token or x_job_token
    if provided_token and not verify_job_access_token(provided_token, str(job.id)):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="ACCESS_DENIED",
            message="Invalid or tampered job access token.",
        )

    channel_name = f"channel:job:{job.id}"

    async def event_generator():
        # 1. Emit initial state immediately
        initial_progress = job.progress
        initial_speed = job.speed
        initial_eta = job.eta
        initial_status = job.status.value

        # Check Redis cached progress overlay
        r = None
        try:
            r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            cached_data = await r.get(f"job:{job.id}:progress")
            if cached_data:
                p_dict = json.loads(cached_data)
                initial_progress = float(p_dict.get("progress", initial_progress))
                initial_speed = p_dict.get("speed", initial_speed)
                initial_eta = p_dict.get("eta", initial_eta)
                initial_status = p_dict.get("status", initial_status)
        except Exception:
            r = None

        initial_payload = {
            "job_id": str(job.id),
            "status": initial_status,
            "progress": initial_progress,
            "speed": initial_speed,
            "eta": initial_eta,
            "file_size": job.file_size,
            "download_url": job.download_url,
            "created_at": job.created_at.isoformat(),
            "expires_at": job.expires_at.isoformat(),
        }
        yield f"data: {json.dumps(initial_payload)}\n\n"

        # If job is already in terminal state, terminate stream immediately
        if initial_status in [
            JobStatus.COMPLETED.value,
            JobStatus.FAILED.value,
            JobStatus.CANCELLED.value,
            JobStatus.EXPIRED.value,
        ]:
            if r:
                await r.aclose()
            return

        # 2. Subscribe to Redis pubsub
        pubsub = None
        if r:
            try:
                pubsub = r.pubsub()
                await pubsub.subscribe(channel_name)
            except Exception:
                pubsub = None

        try:
            last_ping = asyncio.get_event_loop().time()
            while True:
                if await request.is_disconnected():
                    break

                message = None
                if pubsub:
                    try:
                        message = await pubsub.get_message(
                            ignore_subscribe_messages=True, timeout=1.0
                        )
                    except Exception:
                        message = None

                if message and message.get("type") == "message":
                    raw_data = message.get("data")
                    if raw_data:
                        yield f"data: {raw_data}\n\n"
                        try:
                            msg_dict = json.loads(raw_data)
                            st = msg_dict.get("status")
                            if st in [
                                JobStatus.COMPLETED.value,
                                JobStatus.FAILED.value,
                                JobStatus.CANCELLED.value,
                                JobStatus.EXPIRED.value,
                            ]:
                                break
                        except Exception:
                            pass
                else:
                    await asyncio.sleep(0.5)

                now = asyncio.get_event_loop().time()
                if now - last_ping >= 15.0:
                    yield ": keepalive\n\n"
                    last_ping = now

        finally:
            if pubsub:
                try:
                    await pubsub.unsubscribe(channel_name)
                    await pubsub.aclose()
                except Exception:
                    pass
            if r:
                try:
                    await r.aclose()
                except Exception:
                    pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
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
    request: Request,
    token: Optional[str] = Query(None),
    x_job_token: Optional[str] = Header(None, alias="X-Job-Token"),
    db: AsyncSession = Depends(get_db),
) -> JobStatusResponse:
    """Cancels a queued or active job and evicts any partial files."""
    import glob

    stmt = select(DownloadJob).where(DownloadJob.id == job_id)
    res = await db.execute(stmt)
    job = res.scalars().first()

    if not job:
        raise JobNotFoundError("Download job not found.")

    # Verify ownership
    caller_ip_hash = get_client_ip_hash(request)
    auth_token = token or x_job_token
    token_valid = verify_job_access_token(auth_token, str(job.id)) if auth_token else False
    ip_match = (job.ip_hash == caller_ip_hash)

    if not (token_valid or ip_match):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="ACCESS_DENIED",
            message="Unauthorized to cancel this job: missing or invalid job access token.",
        )

    # Signal cancellation in Redis and revoke Celery task if queued/processing
    if job.status in [JobStatus.QUEUED, JobStatus.PROCESSING]:
        if redis_client:
            try:
                redis_client.setex(f"job:{job_id}:cancelled", 3600, "1")
            except Exception:
                pass
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

    # Publish cancellation event to Redis
    try:
        if redis_client:
            redis_client.publish(
                f"channel:job:{job.id}",
                json.dumps({"job_id": str(job.id), "status": "CANCELLED", "progress": 0.0}),
            )
    except Exception:
        pass

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        speed=job.speed,
        eta=job.eta,
        file_size=job.file_size,
        download_url=None,
        job_access_token=generate_job_access_token(str(job.id)) if (token_valid or ip_match) else None,
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
    token: Optional[str] = Query(None),
    x_job_token: Optional[str] = Header(None, alias="X-Job-Token"),
    db: AsyncSession = Depends(get_db),
) -> JobStatusResponse:
    """Retrieves real-time job state and metrics. Accepts UUID or media URL."""
    clean_id_str = urllib.parse.unquote(str(job_id)).strip()
    job = None

    # 1. If user entered a video URL, look up existing job only (no auto-enqueue on GET)
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

        if not job:
            raise JobNotFoundError(
                "No download job found for this URL. Please submit a download request via POST /api/v1/downloads."
            )
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

    caller_ip_hash = get_client_ip_hash(request)
    auth_token = token or x_job_token
    token_valid = verify_job_access_token(auth_token, str(job.id)) if auth_token else False
    ip_match = (job.ip_hash == caller_ip_hash)

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
        job_access_token=generate_job_access_token(str(job.id)) if (token_valid or ip_match) else None,
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
