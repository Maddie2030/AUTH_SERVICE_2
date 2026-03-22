import uuid
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from jose import jwt, JWTError

from app.core.config import settings
from app.core.constants import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)

_ph = PasswordHasher(
    memory_cost=settings.ARGON2_MEMORY_COST,
    time_cost=settings.ARGON2_TIME_COST,
    parallelism=settings.ARGON2_PARALLELISM,
)

ALGORITHM = "RS256"
FALLBACK_ALGORITHM = "HS256"
ISSUER = "mocktest-auth"


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return _ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed_password: str) -> bool:
    return _ph.check_needs_rehash(hashed_password)


def _get_signing_key() -> tuple[str, str]:
    if settings.RS256_PRIVATE_KEY and settings.RS256_PUBLIC_KEY:
        return settings.RS256_PRIVATE_KEY, ALGORITHM
    return settings.SECRET_KEY, FALLBACK_ALGORITHM


def _get_verify_key() -> tuple[str, str]:
    if settings.RS256_PUBLIC_KEY:
        return settings.RS256_PUBLIC_KEY, ALGORITHM
    return settings.SECRET_KEY, FALLBACK_ALGORITHM


def create_access_token(
    subject: str,
    role: str,
    session_id: str,
    token_version: int,
    expires_delta: Optional[timedelta] = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: Dict[str, Any] = {
        "sub": subject,
        "role": role,
        "session_id": session_id,
        "token_version": token_version,
        "iat": datetime.now(timezone.utc),
        "exp": expire,
        "iss": ISSUER,
        "type": "access",
    }
    key, algorithm = _get_signing_key()
    return jwt.encode(payload, key, algorithm=algorithm)


def create_refresh_token(
    subject: str,
    session_id: str,
    token_version: int,
    expires_delta: Optional[timedelta] = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    payload: Dict[str, Any] = {
        "sub": subject,
        "session_id": session_id,
        "token_version": token_version,
        "iat": datetime.now(timezone.utc),
        "exp": expire,
        "iss": ISSUER,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
    }
    key, algorithm = _get_signing_key()
    return jwt.encode(payload, key, algorithm=algorithm)


def decode_token(token: str) -> Dict[str, Any]:
    key, algorithm = _get_verify_key()
    try:
        payload = jwt.decode(
            token, key, algorithms=[algorithm], options={"verify_iss": False}
        )
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e


def generate_secure_token() -> str:
    return secrets.token_urlsafe(32)


def generate_uuid() -> str:
    return str(uuid.uuid4())
