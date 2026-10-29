from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field

from app.models.takedown import TakedownStatus


class TakedownRequest(BaseModel):
    """Payload for submitting a copyright or DMCA takedown claim."""

    requester_name: str = Field(..., min_length=2, max_length=256, description="Full legal name")
    requester_email: EmailStr = Field(..., description="Valid contact email address")
    copyrighted_work_url: str = Field(..., max_length=2048, description="Link to original authorized work")
    infringing_url: str = Field(..., max_length=2048, description="Target media URL to be blocked")
    statement: Optional[str] = Field(default=None, max_length=4000, description="Legal statement / details")
    declaration_truth: bool = Field(
        ...,
        description="Affirmation that information provided is accurate under penalty of perjury",
    )


class TakedownResponse(BaseModel):
    """Acknowledgement of takedown filing."""

    case_id: UUID
    status: TakedownStatus
    message: str
    created_at: datetime

