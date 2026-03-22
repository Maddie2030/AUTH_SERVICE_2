import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, JSON, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base
from app.core.constants import AuditEventType


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_type: Mapped[AuditEventType] = mapped_column(SAEnum(AuditEventType), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} event={self.event_type}>"
