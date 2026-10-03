from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base
import enum


class AIRunStatus(str, enum.Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


class AIRun(Base):
    __tablename__ = "ai_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_version_id = Column(UUID(as_uuid=True), ForeignKey("contract_versions.id"), nullable=False)
    run_id = Column(String(100), nullable=False, unique=True)
    provider = Column(String(50), nullable=False)  # e.g., "openai"
    model = Column(String(100), nullable=False)  # e.g., "gpt-4o-mini"
    status = Column(String(20), default="started")
    duration_ms = Column(Integer, nullable=True)
    validation_result = Column(String(50), nullable=True)  # "passed", "failed"
    error_message = Column(Text, nullable=True)
    response_metadata = Column(JSON, nullable=True)  # Tokens, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    contract_version = relationship("ContractVersion", back_populates="ai_runs")
