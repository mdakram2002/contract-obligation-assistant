from sqlalchemy.ext.asyncio import AsyncSession
from app.models.application_log import ApplicationLog, EventType, LogLevel
from datetime import datetime
import uuid
from typing import Optional, Any


class LoggingService:
    """Service for structured application logging to database."""

    @staticmethod
    async def log_event(
        db: AsyncSession,
        event_type: EventType,
        log_level: LogLevel = LogLevel.INFO,
        contract_id: Optional[str] = None,
        contract_version_id: Optional[str] = None,
        user_id: Optional[str] = None,
        message: Optional[str] = None,
        metadata: Optional[dict] = None
    ):
        """
        Log an application event to the database.
        """
        log_entry = ApplicationLog(
            event_type=event_type,
            log_level=log_level,
            contract_id=uuid.UUID(contract_id) if contract_id else None,
            contract_version_id=uuid.UUID(contract_version_id) if contract_version_id else None,
            user_id=user_id,
            message=message,
            log_metadata=metadata
        )
        db.add(log_entry)
        await db.commit()
