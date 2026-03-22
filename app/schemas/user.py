import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from app.core.constants import UserRole, UserStatus


class UserResponse(BaseModel):
    id: uuid.UUID
    mobile_number: str
    full_name: str
    role: UserRole
    status: UserStatus
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int
    page: int
    page_size: int


class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    session_id: uuid.UUID


class UserProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None

    def model_post_init(self, __context: object) -> None:
        if self.full_name is not None:
            self.full_name = self.full_name.strip()
            if len(self.full_name) < 2:
                raise ValueError("Full name must be at least 2 characters.")
