import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.user import UserResponse, UserProfileUpdateRequest
from app.api.deps import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_my_profile(
    user: User = Depends(get_current_user),
):
    return UserResponse.model_validate(user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
)
async def update_my_profile(
    data: UserProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if data.full_name is not None:
        user.full_name = data.full_name
    await db.flush()
    return UserResponse.model_validate(user)
