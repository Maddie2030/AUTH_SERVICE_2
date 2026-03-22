import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, Request, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.schemas.admin import InviteAdminRequest, AcceptInviteRequest, InvitationResponse
from app.schemas.user import AuthResponse, UserResponse, UserListResponse
from app.models.audit_log import AuditLog
from app.models.user import User
from app.services.admin_service import AdminService
from app.core.constants import UserRole, UserStatus, AuditEventType
from app.api.deps import get_current_user, require_admin, get_client_ip

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post(
    "/invite",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create admin invitation",
)
async def invite_admin(
    data: InviteAdminRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
    ip_address: Optional[str] = Depends(get_client_ip),
):
    request_id = getattr(request.state, "request_id", None)
    svc = AdminService(db)
    invite = await svc.create_invitation(
        mobile_number=data.mobile_number,
        full_name=data.full_name,
        invited_by=admin,
        ip_address=ip_address,
        request_id=request_id,
    )
    return InvitationResponse.model_validate(invite)


@router.post(
    "/accept-invite",
    response_model=AuthResponse,
    summary="Accept admin invitation and set password",
)
async def accept_invite(
    data: AcceptInviteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ip_address: Optional[str] = Depends(get_client_ip),
):
    request_id = getattr(request.state, "request_id", None)
    svc = AdminService(db)
    user, session, access_token, refresh_token, expires_in = await svc.accept_invitation(
        token=data.token,
        password=data.password,
        ip_address=ip_address,
        request_id=request_id,
    )
    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        session_id=session.id,
    )


@router.get(
    "/invitations",
    response_model=List[InvitationResponse],
    summary="List pending admin invitations",
)
async def list_invitations(
    include_accepted: bool = False,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    svc = AdminService(db)
    invites = await svc.list_invitations(include_accepted=include_accepted)
    return [InvitationResponse.model_validate(i) for i in invites]


@router.delete(
    "/invitations/{invite_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a pending invitation",
)
async def revoke_invitation(
    invite_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    request_id = getattr(request.state, "request_id", None)
    svc = AdminService(db)
    await svc.revoke_invitation(invite_id=invite_id, admin=admin, request_id=request_id)


@router.get(
    "/users",
    response_model=UserListResponse,
    summary="List all users",
)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Optional[UserRole] = None,
    status_filter: Optional[UserStatus] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    svc = AdminService(db)
    users, total = await svc.list_users(
        page=page,
        page_size=page_size,
        role=role,
        status=status_filter,
    )
    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Get user details",
)
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    svc = AdminService(db)
    user = await svc.get_user(user_id)
    return UserResponse.model_validate(user)


@router.post(
    "/users/{user_id}/lock",
    response_model=UserResponse,
    summary="Lock a user account",
)
async def lock_user(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
    ip_address: Optional[str] = Depends(get_client_ip),
):
    svc = AdminService(db)
    user = await svc.lock_user(user_id=user_id, admin=admin, ip_address=ip_address)
    return UserResponse.model_validate(user)


@router.post(
    "/users/{user_id}/unlock",
    response_model=UserResponse,
    summary="Unlock a user account",
)
async def unlock_user(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
    ip_address: Optional[str] = Depends(get_client_ip),
):
    svc = AdminService(db)
    user = await svc.unlock_user(user_id=user_id, admin=admin, ip_address=ip_address)
    return UserResponse.model_validate(user)


@router.post(
    "/users/{user_id}/disable",
    response_model=UserResponse,
    summary="Disable a user account",
)
async def disable_user(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
    ip_address: Optional[str] = Depends(get_client_ip),
):
    svc = AdminService(db)
    user = await svc.disable_user(user_id=user_id, admin=admin, ip_address=ip_address)
    return UserResponse.model_validate(user)


@router.post(
    "/users/{user_id}/enable",
    response_model=UserResponse,
    summary="Enable a disabled user account",
)
async def enable_user(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
    ip_address: Optional[str] = Depends(get_client_ip),
):
    svc = AdminService(db)
    user = await svc.enable_user(user_id=user_id, admin=admin, ip_address=ip_address)
    return UserResponse.model_validate(user)


@router.get(
    "/audit-logs",
    summary="Query audit logs",
)
async def query_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user_id: Optional[uuid.UUID] = None,
    event_type: Optional[str] = None,
    ip_address: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    from sqlalchemy import select, func
    from app.core.constants import AuditEventType as AET

    query = select(AuditLog)
    count_query = select(func.count(AuditLog.id))

    if user_id:
        query = query.where(AuditLog.user_id == user_id)
        count_query = count_query.where(AuditLog.user_id == user_id)
    if event_type:
        query = query.where(AuditLog.event_type == event_type)
        count_query = count_query.where(AuditLog.event_type == event_type)
    if ip_address:
        query = query.where(AuditLog.ip_address == ip_address)
        count_query = count_query.where(AuditLog.ip_address == ip_address)
    if from_date:
        query = query.where(AuditLog.created_at >= from_date)
        count_query = count_query.where(AuditLog.created_at >= from_date)
    if to_date:
        query = query.where(AuditLog.created_at <= to_date)
        count_query = count_query.where(AuditLog.created_at <= to_date)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(AuditLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "items": [
            {
                "id": str(log.id),
                "event_type": log.event_type,
                "user_id": str(log.user_id) if log.user_id else None,
                "ip_address": log.ip_address,
                "device_id": log.device_id,
                "metadata": log.metadata_,
                "request_id": log.request_id,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }