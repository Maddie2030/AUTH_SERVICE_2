from enum import Enum


class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class UserStatus(str, Enum):
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    LOCKED = "locked"
    DISABLED = "disabled"


class AuditEventType(str, Enum):
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    REGISTRATION_SUCCESS = "registration_success"
    EXAM_STARTED = "exam_started"
    EXAM_SUBMITTED = "exam_submitted"
    PASSWORD_CHANGED = "password_changed"
    ADMIN_INVITED = "admin_invited"
    ADMIN_INVITE_ACCEPTED = "admin_invite_accepted"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    ACCOUNT_DISABLED = "account_disabled"
    ACCOUNT_ENABLED = "account_enabled"
    SESSION_TERMINATED = "session_terminated"
    LOGOUT = "logout"
    LOGOUT_ALL = "logout_all"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_RESET_COMPLETED = "password_reset_completed"


MAX_FAILED_ATTEMPTS = 5
LOCK_DURATION_MINUTES = 15
MAX_EXAM_DURATION_HOURS = 3
EXAM_GRACE_PERIOD_MINUTES = 10
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7
INVITE_TOKEN_EXPIRE_HOURS = 24
PASSWORD_RESET_TOKEN_EXPIRE_HOURS = 1

RATE_LIMIT_LOGIN = "5/minute"
RATE_LIMIT_REFRESH = "10/minute"
RATE_LIMIT_GENERAL = "100/minute"

ERROR_CODES = {
    "AUTH_001": "Mobile number already registered.",
    "AUTH_002": "Invalid password format.",
    "AUTH_003": "Invalid role specified. Only 'student' or 'teacher' are allowed.",
    "AUTH_010": "The mobile number or password is incorrect.",
    "AUTH_011": "Account not verified. Please accept your admin invitation first.",
    "AUTH_012": "Account is locked due to too many failed login attempts.",
    "AUTH_013": "Account is disabled. Please contact an administrator.",
    "AUTH_014": "Rate limit exceeded. Please try again later.",
    "AUTH_030": "Invalid or expired refresh token.",
    "AUTH_031": "Token has been revoked.",
    "AUTH_032": "Session has expired or been terminated.",
    "AUTH_040": "Invalid or expired invitation token.",
    "AUTH_041": "Invitation has already been accepted.",
    "AUTH_042": "Mobile number already registered.",
    "AUTH_043": "Insufficient permissions.",
    "AUTH_050": "Session not found.",
    "AUTH_051": "An exam session is already active for this user.",
}
