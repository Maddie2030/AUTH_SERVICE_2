import uuid
import logging
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.core.constants import AuditEventType

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        event_type: AuditEventType,
        user_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        device_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        request_id: Optional[str] = None,
    ) -> AuditLog:
        log_entry = AuditLog(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            device_id=device_id,
            metadata_=metadata,
            request_id=request_id,
        )
        self.db.add(log_entry)
        try:
            await self.db.flush()
        except Exception as e:
            logger.warning("Failed to flush audit log: %s", e)
        logger.info(
            "Audit event: %s user=%s ip=%s request_id=%s",
            event_type,
            user_id,
            ip_address,
            request_id,
        )
        return log_entry
