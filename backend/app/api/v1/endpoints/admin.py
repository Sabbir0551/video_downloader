import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.takedown import TakedownRecord, TakedownStatus
from app.schemas.takedown import TakedownResponse

router = APIRouter(prefix="/admin", tags=["Admin"])


def verify_admin_key(x_admin_key: str = Header(..., alias="X-Admin-Key")) -> None:
    """Enforces admin authentication via API key header."""
    if not settings.ADMIN_API_KEY or x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin credentials.",
        )


class TakedownReviewRequest(BaseModel):
    action: str = Field(..., description="'approve' or 'reject'")
    notes: Optional[str] = Field(default=None, description="Admin review rationale")


class AdminTakedownItem(BaseModel):
    id: uuid.UUID
    target_url: str
    channel_id: Optional[str]
    requester_name: str
    requester_email: str
    status: TakedownStatus
    statement: Optional[str]
    created_at: Optional[datetime]
    reviewed_at: Optional[datetime]
    reviewed_by: Optional[str]


@router.get("/takedowns", response_model=List[AdminTakedownItem], dependencies=[Depends(verify_admin_key)])
async def list_admin_takedowns(
    status_filter: Optional[TakedownStatus] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> List[AdminTakedownItem]:
    """Lists submitted takedown notices for administrative inspection."""
    stmt = select(TakedownRecord).order_by(desc(TakedownRecord.created_at)).limit(limit)
    if status_filter:
        stmt = stmt.where(TakedownRecord.status == status_filter)
    res = await db.execute(stmt)
    records = res.scalars().all()
    return [
        AdminTakedownItem(
            id=r.id,
            target_url=r.target_url,
            channel_id=r.channel_id,
            requester_name=r.requester_name,
            requester_email=r.requester_email,
            status=r.status,
            statement=r.statement,
            created_at=r.created_at,
            reviewed_at=r.reviewed_at,
            reviewed_by=r.reviewed_by,
        )
        for r in records
    ]


@router.post("/takedowns/{case_id}/review", response_model=TakedownResponse, dependencies=[Depends(verify_admin_key)])
async def review_takedown(
    case_id: uuid.UUID,
    payload: TakedownReviewRequest,
    db: AsyncSession = Depends(get_db),
) -> TakedownResponse:
    """Approves or rejects a takedown claim."""
    record = await db.get(TakedownRecord, case_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Takedown case {case_id} not found.",
        )

    action_lower = payload.action.strip().lower()
    now = datetime.now(timezone.utc)
    if action_lower == "approve":
        record.status = TakedownStatus.APPROVED
        msg = "Takedown approved. The content is now permanently blocked."
    elif action_lower == "reject":
        record.status = TakedownStatus.REJECTED
        msg = "Takedown rejected. Content unblocked."
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be 'approve' or 'reject'.",
        )

    record.reviewed_at = now
    record.reviewed_by = "admin"
    await db.commit()
    await db.refresh(record)

    return TakedownResponse(
        case_id=record.id,
        status=record.status,
        message=msg,
        created_at=record.created_at or now,
    )
