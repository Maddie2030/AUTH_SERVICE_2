import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.config import settings
from app.core.utils import ensure_utc
from app.models.session import Session
from app.models.user import User
from app.exceptions import SessionNotFoundError, ExamSessionActiveError

logger = logging.getLogger(__name__)


class SessionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(
        self,
        user: User,
        ip_address: Optional[str] = None,
        device_id: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Session:
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        session = Session(
            user_id=user.id,
            ip_address=ip_address,
            device_id=device_id,
            user_agent=user_agent,
            expires_at=expires_at,
            token_version=1,
        )
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_session(self, session_id: uuid.UUID) -> Optional[Session]:
        result = await self.db.execute(
            select(Session).where(Session.id == session_id, Session.is_active == True)
        )
        return result.scalar_one_or_none()

    async def get_user_sessions(self, user_id: uuid.UUID) -> List[Session]:
        result = await self.db.execute(
            select(Session)
            .where(Session.user_id == user_id, Session.is_active == True)
            .order_by(Session.created_at.desc())
        )
        return list(result.scalars().all())

    async def terminate_session(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> Session:
        result = await self.db.execute(
            select(Session).where(
                Session.id == session_id,
                Session.user_id == user_id,
                Session.is_active == True,
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            raise SessionNotFoundError()

        session.is_active = False
        session.refresh_token_hash = None
        await self.db.flush()
        return session

    async def start_exam_session(
        self, session: Session, exam_id: str
    ) -> Session:
        result = await self.db.execute(
            select(Session).where(
                Session.user_id == session.user_id,
                Session.is_exam_active == True,
                Session.is_active == True,
            )
        )
        existing_exam = result.scalar_one_or_none()
        if existing_exam:
            raise ExamSessionActiveError()

        now = datetime.now(timezone.utc)
        exam_expires = now + timedelta(hours=settings.MAX_EXAM_DURATION_HOURS)
        session.is_exam_active = True
        session.exam_id = exam_id
        session.exam_started_at = now
        if ensure_utc(session.expires_at) < exam_expires:
            session.expires_at = exam_expires
        await self.db.flush()
        return session

    async def end_exam_session(self, session: Session) -> Session:
        session.is_exam_active = False
        session.exam_id = None
        await self.db.flush()
        return session

    async def cleanup_expired_exam_sessions(self) -> int:
        max_duration = timedelta(hours=settings.MAX_EXAM_DURATION_HOURS)
        cutoff = datetime.now(timezone.utc) - max_duration
        result = await self.db.execute(
            select(Session).where(
                Session.is_exam_active == True,
                Session.exam_started_at < cutoff,
            )
        )
        sessions = result.scalars().all()
        for s in sessions:
            s.is_exam_active = False
            s.exam_id = None
        await self.db.flush()
        return len(sessions)
