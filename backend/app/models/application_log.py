from sqlalchemy import Column, String, DateTime, Text, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.database import Base
import enum


class LogLevel(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class EventType(str, enum.Enum):
    DOCUMENT_UPLOADED = "document_uploaded"
    TEXT_EXTRACTION_STARTED = "text_extraction_started"
    TEXT_EXTRACTION_COMPLETED = "text_extraction_completed"
    TEXT_EXTRACTION_FAILED = "text_extraction_failed"
    AI_ANALYSIS_STARTED = "ai_analysis_started"
    AI_ANALYSIS_COMPLETED = "ai_analysis_completed"
    AI_ANALYSIS_FAILED = "ai_analysis_failed"
    ITEM_EDITED = "item_edited"
    ITEM_APPROVED = "item_approved"
    ITEM_REJECTED = "item_rejected"
    VERSION_CREATED = "version_created"
    STALE_ITEMS_DETECTED = "stale_items_detected"
    SUMMARY_GENERATED = "summary_generated"


class ApplicationLog(Base):
    __tablename__ = "application_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(50), nullable=False)
    log_level = Column(String(20), default="info")
    contract_id = Column(UUID(as_uuid=True), nullable=True)
    contract_version_id = Column(UUID(as_uuid=True), nullable=True)
    user_id = Column(String(100), nullable=True)  # For future authentication
    message = Column(Text, nullable=True)
    log_metadata = Column(JSON, nullable=True)  # Additional context
    created_at = Column(DateTime, default=datetime.utcnow)
