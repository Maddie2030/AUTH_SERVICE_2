import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SessionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_active: bool
    is_exam_active: bool
    exam_id: Optional[str] = None
    exam_started_at: Optional[datetime] = None
    created_at: datetime
    expires_at: datetime
    last_active_at: datetime

    model_config = {"from_attributes": True}


class StartExamRequest(BaseModel):
    exam_id: str


class EndExamRequest(BaseModel):
    exam_id: str
    reason: str = "submitted"
