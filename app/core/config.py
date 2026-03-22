import os
import secrets
from typing import List
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from pydantic_settings import BaseSettings
from pydantic import field_validator


def _convert_db_url(url: str) -> str:
    if not url:
        return url
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    query_params.pop("sslmode", None)
    new_query = urlencode({k: v[0] for k, v in query_params.items()})
    clean_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment,
    ))
    if clean_url.startswith("postgres://"):
        clean_url = clean_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif clean_url.startswith("postgresql://") and "+asyncpg" not in clean_url:
        clean_url = clean_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return clean_url


class Settings(BaseSettings):
    PROJECT_NAME: str = "MockTest Auth Service"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    DATABASE_URL: str = "sqlite+aiosqlite:///./mocktest_auth.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    SECRET_KEY: str = secrets.token_urlsafe(32)
    SESSION_SECRET: str = secrets.token_urlsafe(32)

    RS256_PRIVATE_KEY: str = ""
    RS256_PUBLIC_KEY: str = ""

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    ARGON2_MEMORY_COST: int = 65536
    ARGON2_TIME_COST: int = 3
    ARGON2_PARALLELISM: int = 4

    LOG_LEVEL: str = "INFO"

    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCK_DURATION_MINUTES: int = 15

    MAX_EXAM_DURATION_HOURS: int = 3
    EXAM_GRACE_PERIOD_MINUTES: int = 10

    INVITE_TOKEN_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 1

    RATE_LIMIT_ENABLED: bool = True

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
    }

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def convert_db_url(cls, v: str) -> str:
        return _convert_db_url(v)

    @field_validator("RS256_PRIVATE_KEY", mode="before")
    @classmethod
    def validate_private_key(cls, v: str) -> str:
        if v:
            return v.replace("\\n", "\n")
        return v

    @field_validator("RS256_PUBLIC_KEY", mode="before")
    @classmethod
    def validate_public_key(cls, v: str) -> str:
        if v:
            return v.replace("\\n", "\n")
        return v


settings = Settings()
