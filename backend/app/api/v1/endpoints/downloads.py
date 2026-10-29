import asyncio
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import (
    ContentBlockedLegalError,
    DRMProtectedError,
    MediaTooLargeError,
    RateLimitExceededError,
)
from app.core.security import hash_ip
from app.core.ssrf import validate_url_security
from app.db.session import get_db
from app.models.job import DownloadJob, JobStatus
from app.models.takedown import TakedownRecord, TakedownStatus
from app.schemas.common import ErrorResponse
from app.schemas.job import CreateJobRequest, JobStatusResponse
from app.services.extractor import extract_media_info
from app.worker.tasks import download_media_task

router = APIRouter()


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
                        "expires_at": "2026-10-30T02:25:00Z",
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
            "description": "Active download concurrency limit exceeded for IP",
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
    },
)
async def create_download_job(
    request: Request,
    payload: CreateJobRequest,
    db: AsyncSession = Depends(get_db),
) -> JobStatusResponse:
    """
    Submits a new background media download job to Celery worker pool.
    """
    # 1. SSRF Pre-Resolution Guard
    clean_url, _ = validate_url_security(payload.url)

    # 2. Check for active legal takedown / blacklist blocks
    url_hash = hashlib.sha256(clean_url.encode("utf-8")).hexdigest()
    takedown_stmt = select(TakedownRecord).where(
        TakedownRecord.url_hash == url_hash,
        TakedownRecord.status != TakedownStatus.REJECTED,
    )
    takedown_res = await db.execute(takedown_stmt)
    if takedown_res.scalars().first():
        raise ContentBlockedLegalError("This content has been blocked due to a copyright or legal notice.")

    # 3. Quick metadata extraction to verify limits & title
    media_info = await asyncio.to_thread(extract_media_info, clean_url)
    if media_info.duration > settings.MAX_VIDEO_DURATION_SECONDS:
        raise MediaTooLargeError(
            f"Video duration ({media_info.duration // 60}m) exceeds platform maximum of {settings.MAX_VIDEO_DURATION_SECONDS // 60}m."
        )

    # 4. Hash client IP (privacy-preserving) & check concurrency cap
    client_ip = request.client.host if request.client else "127.0.0.1"
    ip_hash = hash_ip(client_ip)

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

    # 5. Create database record
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

    # 6. Dispatch background worker task via Celery
    try:
        download_media_task.delay(
            job_id=str(new_job.id),
            url=clean_url,
            format_id=payload.format_id,
            is_audio_only=payload.audio_only,
            title=media_info.title,
        )
    except Exception as err:
        # If Celery broker is temporarily unreachable, mark job failed gracefully
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


# Alias endpoint /jobs to maintain full OpenAPI specification backwards compatibility
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

