import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base
from app.core.constants import UserRole, UserStatus


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mobile_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), nullable=False)
    status: Mapped[UserStatus] = mapped_column(
        SAEnum(UserStatus), nullable=False, default=UserStatus.ACTIVE
    )
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return f"<User id={self.id} mobile={self.mobile_number} role={self.role}>"
