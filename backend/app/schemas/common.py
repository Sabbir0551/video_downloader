from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Structured error payload returned on API failures."""

    error_code: str = Field(..., description="Machine-readable error identifier")
    message: str = Field(..., description="Sanitized, localized human-friendly error explanation")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Optional diagnostic attributes")

    model_config = {
        "json_schema_extra": {
            "example": {
                "error_code": "SSRF_DESTINATION_FORBIDDEN",
                "message": "The requested host destination is restricted.",
                "details": {"hostname": "169.254.169.254"},
            }
        }
    }

