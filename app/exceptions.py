from typing import Optional, Any
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

logger = logging.getLogger(__name__)


class AppException(Exception):
    def __init__(
        self,
        message: str,
        code: str,
        http_status: int = status.HTTP_400_BAD_REQUEST,
        error_type: Optional[str] = None,
        details: Optional[Any] = None,
    ):
        self.message = message
        self.code = code
        self.http_status = http_status
        self.error_type = error_type or self.__class__.__name__
        self.details = details
        super().__init__(message)


class AuthenticationError(AppException):
    pass


class InvalidCredentialsError(AuthenticationError):
    def __init__(self):
        super().__init__(
            message="The mobile number or password is incorrect.",
            code="AUTH_010",
            http_status=status.HTTP_401_UNAUTHORIZED,
        )


class AccountLockedError(AuthenticationError):
    def __init__(self, locked_until=None):
        details = {"locked_until": str(locked_until)} if locked_until else {}
        super().__init__(
            message="Account is locked due to too many failed login attempts.",
            code="AUTH_012",
            http_status=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class AccountDisabledError(AuthenticationError):
    def __init__(self):
        super().__init__(
            message="Account is disabled. Please contact an administrator.",
            code="AUTH_013",
            http_status=status.HTTP_403_FORBIDDEN,
        )


class AccountNotVerifiedError(AuthenticationError):
    def __init__(self):
        super().__init__(
            message="Account not verified. Please accept your admin invitation first.",
            code="AUTH_011",
            http_status=status.HTTP_403_FORBIDDEN,
        )


class MobileAlreadyRegisteredError(AppException):
    def __init__(self):
        super().__init__(
            message="Mobile number already registered.",
            code="AUTH_001",
            http_status=status.HTTP_409_CONFLICT,
        )


class InvalidRoleError(AppException):
    def __init__(self):
        super().__init__(
            message="Invalid role specified. Only 'student' or 'teacher' are allowed.",
            code="AUTH_003",
            http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class TokenError(AppException):
    pass


class TokenExpiredError(TokenError):
    def __init__(self):
        super().__init__(
            message="Invalid or expired refresh token.",
            code="AUTH_030",
            http_status=status.HTTP_401_UNAUTHORIZED,
        )


class TokenInvalidError(TokenError):
    def __init__(self):
        super().__init__(
            message="Invalid or expired refresh token.",
            code="AUTH_030",
            http_status=status.HTTP_401_UNAUTHORIZED,
        )


class TokenVersionMismatchError(TokenError):
    def __init__(self):
        super().__init__(
            message="Token has been revoked.",
            code="AUTH_031",
            http_status=status.HTTP_401_UNAUTHORIZED,
        )


class SessionError(AppException):
    pass


class SessionExpiredError(SessionError):
    def __init__(self):
        super().__init__(
            message="Session has expired or been terminated.",
            code="AUTH_032",
            http_status=status.HTTP_401_UNAUTHORIZED,
        )


class SessionNotFoundError(SessionError):
    def __init__(self):
        super().__init__(
            message="Session not found.",
            code="AUTH_050",
            http_status=status.HTTP_404_NOT_FOUND,
        )


class ExamSessionActiveError(SessionError):
    def __init__(self):
        super().__init__(
            message="An exam session is already active for this user.",
            code="AUTH_051",
            http_status=status.HTTP_409_CONFLICT,
        )


class InvitationError(AppException):
    pass


class InvitationExpiredError(InvitationError):
    def __init__(self):
        super().__init__(
            message="Invalid or expired invitation token.",
            code="AUTH_040",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


class InvitationAlreadyAcceptedError(InvitationError):
    def __init__(self):
        super().__init__(
            message="Invitation has already been accepted.",
            code="AUTH_041",
            http_status=status.HTTP_409_CONFLICT,
        )


class InvitationInvalidError(InvitationError):
    def __init__(self):
        super().__init__(
            message="Invalid or expired invitation token.",
            code="AUTH_040",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


class RateLimitError(AppException):
    def __init__(self):
        super().__init__(
            message="Rate limit exceeded. Please try again later.",
            code="AUTH_014",
            http_status=status.HTTP_429_TOO_MANY_REQUESTS,
        )


class PermissionDeniedError(AppException):
    def __init__(self):
        super().__init__(
            message="Insufficient permissions.",
            code="AUTH_043",
            http_status=status.HTTP_403_FORBIDDEN,
        )


def _error_response(
    request_id: Optional[str],
    error_type: str,
    message: str,
    code: str,
) -> dict:
    return {
        "success": False,
        "error": {
            "type": error_type,
            "message": message,
            "code": code,
            "request_id": request_id,
        },
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=exc.http_status,
            content=_error_response(request_id, exc.error_type, exc.message, exc.code),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        errors = exc.errors()
        message = errors[0]["msg"] if errors else "Validation error."
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_response(request_id, "ValidationError", message, "VALIDATION_ERROR"),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_response(
                request_id, "HTTPException", exc.detail or "An error occurred.", "HTTP_ERROR"
            ),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_response(
                request_id,
                "InternalServerError",
                "An unexpected error occurred.",
                "INTERNAL_ERROR",
            ),
        )
