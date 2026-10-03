from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base
import enum


class ItemType(str, enum.Enum):
    EFFECTIVE_DATE = "effective_date"
    EXPIRY = "expiry"
    RENEWAL = "renewal"
    TERMINATION = "termination"
    NOTICE = "notice"


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_CLARIFICATION = "needs_clarification"


class CertaintyLevel(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ExtractedItem(Base):
    __tablename__ = "extracted_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_version_id = Column(UUID(as_uuid=True), ForeignKey("contract_versions.id"), nullable=False)
    item_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    value = Column(Text, nullable=True)
    date_value = Column(DateTime, nullable=True)
    notice_period_days = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    conditions = Column(Text, nullable=True)
    purpose = Column(String(100), nullable=True)
    automatic = Column(String(10), nullable=True)  # "true", "false", or null
    certainty = Column(String(20), default="medium")
    source_section = Column(String(100), nullable=True)
    source_page = Column(Integer, nullable=True)
    source_quote = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    review_status = Column(String(50), default="pending")
    is_stale = Column(String(10), default="false")  # "true" or "false"
    user_edited = Column(String(10), default="false")  # "true" or "false"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    contract_version = relationship("ContractVersion", back_populates="extracted_items")
    review_actions = relationship("ReviewAction", back_populates="extracted_item", cascade="all, delete-orphan")
