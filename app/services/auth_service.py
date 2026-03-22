import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    needs_rehash,
    generate_secure_token,
)
from app.core.utils import ensure_utc
from app.core.constants import (
    UserRole,
    UserStatus,
    AuditEventType,
    MAX_FAILED_ATTEMPTS,
)
from app.models.user import User
from app.models.session import Session
from app.schemas.auth import RegisterRequest, LoginRequest
from app.services.session_service import SessionService
from app.services.token_service import TokenService
from app.services.audit_service import AuditService
from app.exceptions import (
    MobileAlreadyRegisteredError,
    InvalidCredentialsError,
    AccountLockedError,
    AccountDisabledError,
    AccountNotVerifiedError,
)

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.session_svc = SessionService(db)
        self.token_svc = TokenService(db)
        self.audit_svc = AuditService(db)

    async def register(
        self,
        data: RegisterRequest,
        ip_address: Optional[str] = None,
        device_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Tuple[User, Session, str, str, int]:
        existing = await self.db.execute(
            select(User).where(User.mobile_number == data.mobile_number)
        )
        if existing.scalar_one_or_none():
            raise MobileAlreadyRegisteredError()

        user = User(
            mobile_number=data.mobile_number,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
            role=data.role,
            status=UserStatus.ACTIVE,
        )
        self.db.add(user)
        await self.db.flush()

        session = await self.session_svc.create_session(
            user=user,
            ip_address=ip_address,
            device_id=device_id,
        )

        access_token, refresh_token, expires_in = await self.token_svc.issue_tokens(
            user=user, session=session
        )

        await self.audit_svc.log(
            event_type=AuditEventType.REGISTRATION_SUCCESS,
            user_id=user.id,
            ip_address=ip_address,
            device_id=device_id,
            metadata={"role": user.role.value},
            request_id=request_id,
        )

        return user, session, access_token, refresh_token, expires_in

    async def login(
        self,
        data: LoginRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Tuple[User, Session, str, str, int]:
        result = await self.db.execute(
            select(User).where(User.mobile_number == data.mobile_number)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(data.password, user.hashed_password):
            if user:
                await self._handle_failed_attempt(user, ip_address, data.device_id, request_id)
            else:
                await self.audit_svc.log(
                    event_type=AuditEventType.LOGIN_FAILED,
                    ip_address=ip_address,
                    metadata={"mobile_number": data.mobile_number},
                    request_id=request_id,
                )
            raise InvalidCredentialsError()

        if user.status == UserStatus.PENDING_VERIFICATION:
            raise AccountNotVerifiedError()

        if user.status == UserStatus.LOCKED:
            if user.locked_until and ensure_utc(user.locked_until) > datetime.now(timezone.utc):
                raise AccountLockedError(locked_until=user.locked_until)
            user.status = UserStatus.ACTIVE
            user.failed_login_attempts = 0
            user.locked_until = None

        if user.status == UserStatus.DISABLED:
            raise AccountDisabledError()

        if needs_rehash(user.hashed_password):
            user.hashed_password = hash_password(data.password)

        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.flush()

        session = await self.session_svc.create_session(
            user=user,
            ip_address=ip_address,
            device_id=data.device_id,
            user_agent=user_agent,
        )

        access_token, refresh_token, expires_in = await self.token_svc.issue_tokens(
            user=user, session=session
        )

        await self.audit_svc.log(
            event_type=AuditEventType.LOGIN_SUCCESS,
            user_id=user.id,
            ip_address=ip_address,
            device_id=data.device_id,
            metadata={"session_id": str(session.id)},
            request_id=request_id,
        )

        return user, session, access_token, refresh_token, expires_in

    async def _handle_failed_attempt(
        self,
        user: User,
        ip_address: Optional[str],
        device_id: Optional[str],
        request_id: Optional[str],
    ) -> None:
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            user.status = UserStatus.LOCKED
            user.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=settings.ACCOUNT_LOCK_DURATION_MINUTES
            )
            await self.audit_svc.log(
                event_type=AuditEventType.ACCOUNT_LOCKED,
                user_id=user.id,
                ip_address=ip_address,
                device_id=device_id,
                metadata={"failed_attempts": user.failed_login_attempts},
                request_id=request_id,
            )
        await self.audit_svc.log(
            event_type=AuditEventType.LOGIN_FAILED,
            user_id=user.id,
            ip_address=ip_address,
            device_id=device_id,
            metadata={"failed_attempts": user.failed_login_attempts},
            request_id=request_id,
        )
        await self.db.commit()

    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise InvalidCredentialsError()

        user.hashed_password = hash_password(new_password)
        user.token_version += 1

        await self.db.execute(
            update(Session)
            .where(Session.user_id == user.id, Session.is_active == True)
            .values(is_active=False)
        )

        await self.audit_svc.log(
            event_type=AuditEventType.PASSWORD_CHANGED,
            user_id=user.id,
            ip_address=ip_address,
            request_id=request_id,
        )
        await self.db.flush()

    async def initiate_password_reset(
        self,
        mobile_number: str,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Optional[str]:
        result = await self.db.execute(
            select(User).where(User.mobile_number == mobile_number)
        )
        user = result.scalar_one_or_none()
        if not user or user.status != UserStatus.ACTIVE:
            return None

        token = generate_secure_token()
        reset_expires = datetime.now(timezone.utc) + timedelta(
            hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS
        )

        user.token_version += 1
        await self.db.flush()

        await self.audit_svc.log(
            event_type=AuditEventType.PASSWORD_RESET_REQUESTED,
            user_id=user.id,
            ip_address=ip_address,
            metadata={"token_partial": token[:8] + "..."},
            request_id=request_id,
        )

        return token
