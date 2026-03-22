import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.config import settings
from app.core.security import hash_password, generate_secure_token
from app.core.utils import ensure_utc
from app.core.constants import UserRole, UserStatus, AuditEventType
from app.models.user import User
from app.models.admin_invite import AdminInvite
from app.models.session import Session
from app.services.session_service import SessionService
from app.services.token_service import TokenService
from app.services.audit_service import AuditService
from app.exceptions import (
    MobileAlreadyRegisteredError,
    InvitationInvalidError,
    InvitationExpiredError,
    InvitationAlreadyAcceptedError,
    PermissionDeniedError,
    SessionNotFoundError,
)

logger = logging.getLogger(__name__)


class AdminService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.session_svc = SessionService(db)
        self.token_svc = TokenService(db)
        self.audit_svc = AuditService(db)

    async def create_invitation(
        self,
        mobile_number: str,
        full_name: str,
        invited_by: User,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> AdminInvite:
        if invited_by.role != UserRole.ADMIN:
            raise PermissionDeniedError()

        existing = await self.db.execute(
            select(User).where(User.mobile_number == mobile_number)
        )
        if existing.scalar_one_or_none():
            raise MobileAlreadyRegisteredError()

        token = generate_secure_token()
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=settings.INVITE_TOKEN_EXPIRE_HOURS
        )

        new_admin = User(
            mobile_number=mobile_number,
            full_name=full_name,
            hashed_password="PENDING",
            role=UserRole.ADMIN,
            status=UserStatus.PENDING_VERIFICATION,
        )
        self.db.add(new_admin)
        await self.db.flush()

        invite = AdminInvite(
            invited_user_id=new_admin.id,
            invited_by_id=invited_by.id,
            token=token,
            expires_at=expires_at,
        )
        self.db.add(invite)
        await self.db.flush()

        await self.audit_svc.log(
            event_type=AuditEventType.ADMIN_INVITED,
            user_id=invited_by.id,
            ip_address=ip_address,
            metadata={
                "invited_user_id": str(new_admin.id),
                "invited_mobile": mobile_number,
            },
            request_id=request_id,
        )

        return invite

    async def accept_invitation(
        self,
        token: str,
        password: str,
        ip_address: Optional[str] = None,
        device_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Tuple[User, Session, str, str, int]:
        result = await self.db.execute(
            select(AdminInvite).where(AdminInvite.token == token)
        )
        invite = result.scalar_one_or_none()

        if not invite:
            raise InvitationInvalidError()

        if invite.is_accepted:
            raise InvitationAlreadyAcceptedError()

        if ensure_utc(invite.expires_at) < datetime.now(timezone.utc):
            raise InvitationExpiredError()

        result = await self.db.execute(
            select(User).where(User.id == invite.invited_user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise InvitationInvalidError()

        user.hashed_password = hash_password(password)
        user.status = UserStatus.ACTIVE
        invite.is_accepted = True
        invite.accepted_at = datetime.now(timezone.utc)
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
            event_type=AuditEventType.ADMIN_INVITE_ACCEPTED,
            user_id=user.id,
            ip_address=ip_address,
            request_id=request_id,
        )

        return user, session, access_token, refresh_token, expires_in

    async def list_invitations(
        self, include_accepted: bool = False
    ) -> List[AdminInvite]:
        query = select(AdminInvite)
        if not include_accepted:
            query = query.where(AdminInvite.is_accepted == False)
        result = await self.db.execute(query.order_by(AdminInvite.created_at.desc()))
        return list(result.scalars().all())

    async def revoke_invitation(
        self, invite_id: uuid.UUID, admin: User, request_id: Optional[str] = None
    ) -> None:
        if admin.role != UserRole.ADMIN:
            raise PermissionDeniedError()

        result = await self.db.execute(
            select(AdminInvite).where(
                AdminInvite.id == invite_id,
                AdminInvite.is_accepted == False,
            )
        )
        invite = result.scalar_one_or_none()
        if not invite:
            raise SessionNotFoundError()

        result = await self.db.execute(
            select(User).where(User.id == invite.invited_user_id)
        )
        user = result.scalar_one_or_none()
        if user and user.status == UserStatus.PENDING_VERIFICATION:
            user.is_deleted = True

        await self.db.delete(invite)
        await self.db.flush()

    async def list_users(
        self,
        page: int = 1,
        page_size: int = 20,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None,
    ) -> Tuple[List[User], int]:
        query = select(User).where(User.is_deleted == False)
        count_query = select(func.count(User.id)).where(User.is_deleted == False)

        if role:
            query = query.where(User.role == role)
            count_query = count_query.where(User.role == role)
        if status:
            query = query.where(User.status == status)
            count_query = count_query.where(User.status == status)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        users = list(result.scalars().all())

        return users, total

    async def get_user(self, user_id: uuid.UUID) -> User:
        result = await self.db.execute(
            select(User).where(User.id == user_id, User.is_deleted == False)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise SessionNotFoundError()
        return user

    async def lock_user(
        self,
        user_id: uuid.UUID,
        admin: User,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> User:
        user = await self.get_user(user_id)
        user.status = UserStatus.LOCKED
        user.locked_until = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCOUNT_LOCK_DURATION_MINUTES
        )
        await self.audit_svc.log(
            event_type=AuditEventType.ACCOUNT_LOCKED,
            user_id=user.id,
            ip_address=ip_address,
            metadata={"locked_by": str(admin.id)},
            request_id=request_id,
        )
        await self.db.flush()
        return user

    async def unlock_user(
        self,
        user_id: uuid.UUID,
        admin: User,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> User:
        user = await self.get_user(user_id)
        user.status = UserStatus.ACTIVE
        user.failed_login_attempts = 0
        user.locked_until = None
        await self.audit_svc.log(
            event_type=AuditEventType.ACCOUNT_UNLOCKED,
            user_id=user.id,
            ip_address=ip_address,
            metadata={"unlocked_by": str(admin.id)},
            request_id=request_id,
        )
        await self.db.flush()
        return user

    async def disable_user(
        self,
        user_id: uuid.UUID,
        admin: User,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> User:
        user = await self.get_user(user_id)
        user.status = UserStatus.DISABLED
        await self.audit_svc.log(
            event_type=AuditEventType.ACCOUNT_DISABLED,
            user_id=user.id,
            ip_address=ip_address,
            metadata={"disabled_by": str(admin.id)},
            request_id=request_id,
        )
        await self.db.flush()
        return user

    async def enable_user(
        self,
        user_id: uuid.UUID,
        admin: User,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> User:
        user = await self.get_user(user_id)
        user.status = UserStatus.ACTIVE
        await self.audit_svc.log(
            event_type=AuditEventType.ACCOUNT_ENABLED,
            user_id=user.id,
            ip_address=ip_address,
            metadata={"enabled_by": str(admin.id)},
            request_id=request_id,
        )
        await self.db.flush()
        return user
