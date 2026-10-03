from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base
from app.models.extracted_item import ReviewStatus, CertaintyLevel


class Obligation(Base):
    __tablename__ = "obligations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_version_id = Column(UUID(as_uuid=True), ForeignKey("contract_versions.id"), nullable=False)
    description = Column(Text, nullable=False)
    responsible_party = Column(String(255), nullable=True)
    deadline = Column(DateTime, nullable=True)
    deadline_description = Column(Text, nullable=True)
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
    contract_version = relationship("ContractVersion", back_populates="obligations")
    review_actions = relationship("ReviewAction", back_populates="obligation", cascade="all, delete-orphan")
