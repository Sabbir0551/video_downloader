import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.takedown import TakedownRecord, TakedownStatus
from app.schemas.common import ErrorResponse
from app.schemas.takedown import TakedownRequest, TakedownResponse

router = APIRouter()


@router.post(
    "/takedown",
    response_model=TakedownResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a DMCA or legal copyright takedown notice",
    description="Allows rights holders to submit takedown notices. Immediately flags the target URL for blocking pending administrative review.",
    responses={
        201: {"model": TakedownResponse, "description": "Takedown notice registered and queued for verification"},
        400: {"model": ErrorResponse, "description": "Missing mandatory legal declaration or invalid parameters"},
    },
)
async def submit_takedown(
    payload: TakedownRequest,
    db: AsyncSession = Depends(get_db),
) -> TakedownResponse:
    """Processes incoming copyright takedown notice and enqueues automatic URL block."""
    if not payload.declaration_truth:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Declaration of truth under penalty of perjury is mandatory.",
        )

    clean_target = str(payload.infringing_url).strip()
    url_hash = hashlib.sha256(clean_target.encode("utf-8")).hexdigest()

    record = TakedownRecord(
        id=uuid.uuid4(),
        url_hash=url_hash,
        target_url=clean_target,
        copyrighted_work_url=str(payload.copyrighted_work_url).strip(),
        requester_name=payload.requester_name.strip(),
        requester_email=str(payload.requester_email).strip().lower(),
        statement=payload.statement,
        status=TakedownStatus.BLOCKED_PENDING_REVIEW,
    )

    db.add(record)
    await db.commit()
    await db.refresh(record)

    return TakedownResponse(
        case_id=record.id,
        status=record.status,
        message="DMCA takedown notice registered successfully. The target URL has been blocked pending review.",
        created_at=record.created_at or datetime.now(timezone.utc),
    )
