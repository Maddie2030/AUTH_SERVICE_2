import uuid
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.session import SessionResponse, StartExamRequest, EndExamRequest
from app.services.session_service import SessionService
from app.services.audit_service import AuditService
from app.core.constants import AuditEventType
from app.api.deps import (
    get_current_user,
    get_current_user_and_session,
    get_client_ip,
)
from app.models.user import User
from app.models.session import Session
from app.core.redis import publish_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.get(
    "",
    response_model=List[SessionResponse],
    summary="List active sessions for current user",
)
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = SessionService(db)
    sessions = await svc.get_user_sessions(user.id)
    return [SessionResponse.model_validate(s) for s in sessions]


@router.get(
    "/current",
    response_model=SessionResponse,
    summary="Get current session details",
)
async def get_current_session_endpoint(
    user_and_session: tuple[User, Session] = Depends(get_current_user_and_session),
):
    _, session = user_and_session
    return SessionResponse.model_validate(session)


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Terminate a specific session",
)
async def terminate_session(
    session_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    request_id = getattr(request.state, "request_id", None)
    ip_address = request.client.host if request.client else None
    svc = SessionService(db)
    await svc.terminate_session(session_id=session_id, user_id=user.id)
    audit_svc = AuditService(db)
    await audit_svc.log(
        event_type=AuditEventType.SESSION_TERMINATED,
        user_id=user.id,
        ip_address=ip_address,
        metadata={"session_id": str(session_id)},
        request_id=request_id,
    )


@router.post(
    "/exam/start",
    response_model=SessionResponse,
    summary="Start an exam session",
)
async def start_exam(
    data: StartExamRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_and_session: tuple[User, Session] = Depends(get_current_user_and_session),
    ip_address: Optional[str] = Depends(get_client_ip),
):
    request_id = getattr(request.state, "request_id", None)
    user, session = user_and_session
    svc = SessionService(db)
    updated_session = await svc.start_exam_session(session=session, exam_id=data.exam_id)
    audit_svc = AuditService(db)
    await audit_svc.log(
        event_type=AuditEventType.EXAM_STARTED,
        user_id=user.id,
        ip_address=ip_address,
        metadata={"exam_id": data.exam_id, "session_id": str(session.id)},
        request_id=request_id,
    )
    await publish_event(
        "exam_session_started",
        {
            "user_id": str(user.id),
            "session_id": str(session.id),
            "exam_id": data.exam_id,
        },
    )
    return SessionResponse.model_validate(updated_session)


@router.post(
    "/exam/end",
    response_model=SessionResponse,
    summary="End an active exam session",
)
async def end_exam(
    data: EndExamRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_and_session: tuple[User, Session] = Depends(get_current_user_and_session),
    ip_address: Optional[str] = Depends(get_client_ip),
):
    request_id = getattr(request.state, "request_id", None)
    user, session = user_and_session
    svc = SessionService(db)
    updated_session = await svc.end_exam_session(session)
    audit_svc = AuditService(db)
    await audit_svc.log(
        event_type=AuditEventType.EXAM_SUBMITTED,
        user_id=user.id,
        ip_address=ip_address,
        metadata={"exam_id": data.exam_id, "reason": data.reason},
        request_id=request_id,
    )
    await publish_event(
        "exam_session_ended",
        {
            "user_id": str(user.id),
            "session_id": str(session.id),
            "exam_id": data.exam_id,
            "reason": data.reason,
        },
    )
    return SessionResponse.model_validate(updated_session)
