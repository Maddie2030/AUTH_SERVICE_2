import uuid
import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import decode_token
from app.core.constants import UserRole, UserStatus
from app.db.session import get_db
from app.models.user import User
from app.models.session import Session
from app.exceptions import (
    TokenInvalidError,
    TokenVersionMismatchError,
    SessionExpiredError,
    PermissionDeniedError,
    AccountDisabledError,
    AccountLockedError,
)

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user_and_session(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> tuple[User, Session]:
    if not credentials:
        raise TokenInvalidError()

    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        raise TokenInvalidError()

    if payload.get("type") != "access":
        raise TokenInvalidError()

    user_id = payload.get("sub")
    session_id = payload.get("session_id")
    token_version = payload.get("token_version")

    if not user_id or not session_id:
        raise TokenInvalidError()

    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id), User.is_deleted == False)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise TokenInvalidError()

    if user.status == UserStatus.DISABLED:
        raise AccountDisabledError()
    if user.status == UserStatus.LOCKED:
        raise AccountLockedError()

    result = await db.execute(
        select(Session).where(
            Session.id == uuid.UUID(session_id),
            Session.is_active == True,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise SessionExpiredError()

    if session.token_version != token_version:
        raise TokenVersionMismatchError()

    return user, session


async def get_current_user(
    user_and_session: tuple[User, Session] = Depends(get_current_user_and_session),
) -> User:
    return user_and_session[0]


async def get_current_session(
    user_and_session: tuple[User, Session] = Depends(get_current_user_and_session),
) -> Session:
    return user_and_session[1]


async def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    if user.role != UserRole.ADMIN:
        raise PermissionDeniedError()
    return user


async def get_client_ip(request: Request) -> Optional[str]:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else None


async def get_user_agent(request: Request) -> Optional[str]:
    return request.headers.get("User-Agent")
