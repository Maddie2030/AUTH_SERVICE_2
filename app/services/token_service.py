import uuid
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.utils import ensure_utc
from app.core.constants import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from app.models.session import Session
from app.models.user import User
from app.exceptions import (
    TokenInvalidError,
    TokenVersionMismatchError,
    SessionExpiredError,
)

logger = logging.getLogger(__name__)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class TokenService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def issue_tokens(
        self, user: User, session: Session
    ) -> Tuple[str, str, int]:
        access_token = create_access_token(
            subject=str(user.id),
            role=user.role.value,
            session_id=str(session.id),
            token_version=session.token_version,
        )
        refresh_token = create_refresh_token(
            subject=str(user.id),
            session_id=str(session.id),
            token_version=session.token_version,
        )
        session.refresh_token_hash = _hash_token(refresh_token)
        await self.db.flush()
        return access_token, refresh_token, ACCESS_TOKEN_EXPIRE_MINUTES * 60

    async def refresh_tokens(
        self, refresh_token: str
    ) -> Tuple[str, str, int, Session, User]:
        try:
            payload = decode_token(refresh_token)
        except ValueError:
            raise TokenInvalidError()

        if payload.get("type") != "refresh":
            raise TokenInvalidError()

        session_id = payload.get("session_id")
        token_version = payload.get("token_version")
        user_id = payload.get("sub")

        if not session_id or not user_id:
            raise TokenInvalidError()

        result = await self.db.execute(
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

        if _hash_token(refresh_token) != session.refresh_token_hash:
            raise TokenInvalidError()

        if ensure_utc(session.expires_at) < datetime.now(timezone.utc):
            raise SessionExpiredError()

        result = await self.db.execute(
            select(User).where(User.id == uuid.UUID(user_id))
        )
        user = result.scalar_one_or_none()
        if not user:
            raise TokenInvalidError()

        session.token_version += 1
        new_access_token = create_access_token(
            subject=str(user.id),
            role=user.role.value,
            session_id=str(session.id),
            token_version=session.token_version,
        )
        new_refresh_token = create_refresh_token(
            subject=str(user.id),
            session_id=str(session.id),
            token_version=session.token_version,
        )
        session.refresh_token_hash = _hash_token(new_refresh_token)
        session.last_active_at = datetime.now(timezone.utc)
        await self.db.flush()

        return new_access_token, new_refresh_token, ACCESS_TOKEN_EXPIRE_MINUTES * 60, session, user

    async def revoke_session(self, session: Session) -> None:
        session.is_active = False
        session.refresh_token_hash = None
        await self.db.flush()

    async def revoke_all_user_sessions(self, user: User) -> None:
        user.token_version += 1
        await self.db.execute(
            update(Session)
            .where(Session.user_id == user.id, Session.is_active == True)
            .values(is_active=False, refresh_token_hash=None)
        )
        await self.db.flush()
