import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from app.schemas.auth import MOBILE_REGEX
from pydantic import field_validator


class InviteAdminRequest(BaseModel):
    mobile_number: str
    full_name: str

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        v = v.strip()
        if not MOBILE_REGEX.match(v):
            raise ValueError("Invalid mobile number format.")
        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Full name must be at least 2 characters.")
        return v


class AcceptInviteRequest(BaseModel):
    token: str
    password: str
    confirm_password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        from app.schemas.auth import PASSWORD_REGEX
        if not PASSWORD_REGEX.match(v):
            raise ValueError(
                "Password must be at least 8 characters and contain uppercase, lowercase, digit, and special character."
            )
        return v

    def model_post_init(self, __context: object) -> None:
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")


class InvitationResponse(BaseModel):
    id: uuid.UUID
    invited_user_id: uuid.UUID
    invited_by_id: Optional[uuid.UUID] = None
    token: str
    is_accepted: bool
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}
