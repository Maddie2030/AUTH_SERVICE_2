import logging
from typing import Optional

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.schemas.token import RefreshTokenRequest
from app.schemas.user import AuthResponse, UserResponse
from app.services.auth_service import AuthService
from app.services.token_service import TokenService
from app.services.audit_service import AuditService
from app.core.constants import AuditEventType
from app.api.deps import (
    get_current_user,
    get_current_user_and_session,
    get_client_ip,
    get_user_agent,
)
from app.models.user import User
from app.models.session import Session
from app.exceptions import RateLimitError
from app.core.redis import check_rate_limit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new student or teacher account",
)
async def register(
    data: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ip_address: Optional[str] = Depends(get_client_ip),
):
    request_id = getattr(request.state, "request_id", None)
    auth_svc = AuthService(db)
    user, session, access_token, refresh_token, expires_in = await auth_svc.register(
        data=data,
        ip_address=ip_address,
        device_id=None,
        request_id=request_id,
    )
    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        session_id=session.id,
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login with mobile number and password",
)
async def login(
    data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ip_address: Optional[str] = Depends(get_client_ip),
    user_agent: Optional[str] = Depends(get_user_agent),
):
    request_id = getattr(request.state, "request_id", None)

    rate_key = f"rate:login:{data.mobile_number}"
    allowed = await check_rate_limit(rate_key, limit=5, window_seconds=60)
    if not allowed:
        raise RateLimitError()

    auth_svc = AuthService(db)
    user, session, access_token, refresh_token, expires_in = await auth_svc.login(
        data=data,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )
    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        session_id=session.id,
    )


@router.post(
    "/refresh",
    response_model=AuthResponse,
    summary="Refresh access token",
)
async def refresh_token(
    data: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ip_address: Optional[str] = Depends(get_client_ip),
):
    request_id = getattr(request.state, "request_id", None)
    token_svc = TokenService(db)
    new_access, new_refresh, expires_in, session, user = await token_svc.refresh_tokens(
        data.refresh_token
    )
    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=expires_in,
        session_id=session.id,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout current session",
)
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_and_session: tuple[User, Session] = Depends(get_current_user_and_session),
):
    request_id = getattr(request.state, "request_id", None)
    user, session = user_and_session
    ip_address = request.client.host if request.client else None
    token_svc = TokenService(db)
    await token_svc.revoke_session(session)
    audit_svc = AuditService(db)
    await audit_svc.log(
        event_type=AuditEventType.LOGOUT,
        user_id=user.id,
        ip_address=ip_address,
        metadata={"session_id": str(session.id)},
        request_id=request_id,
    )


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout from all devices",
)
async def logout_all(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_and_session: tuple[User, Session] = Depends(get_current_user_and_session),
):
    request_id = getattr(request.state, "request_id", None)
    user, session = user_and_session
    ip_address = request.client.host if request.client else None
    token_svc = TokenService(db)
    await token_svc.revoke_all_user_sessions(user)
    audit_svc = AuditService(db)
    await audit_svc.log(
        event_type=AuditEventType.LOGOUT_ALL,
        user_id=user.id,
        ip_address=ip_address,
        request_id=request_id,
    )


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change password",
)
async def change_password(
    data: ChangePasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    request_id = getattr(request.state, "request_id", None)
    ip_address = request.client.host if request.client else None
    auth_svc = AuthService(db)
    await auth_svc.change_password(
        user=user,
        current_password=data.current_password,
        new_password=data.new_password,
        ip_address=ip_address,
        request_id=request_id,
    )


@router.post(
    "/forgot-password",
    summary="Initiate password reset",
)
async def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ip_address: Optional[str] = Depends(get_client_ip),
):
    request_id = getattr(request.state, "request_id", None)
    auth_svc = AuthService(db)
    token = await auth_svc.initiate_password_reset(
        mobile_number=data.mobile_number,
        ip_address=ip_address,
        request_id=request_id,
    )
    return {
        "success": True,
        "message": "If your mobile number is registered, a password reset token has been generated.",
        "reset_token": token,
    }