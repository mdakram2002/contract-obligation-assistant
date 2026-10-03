from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base
import enum


class ActionType(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"
    CLARIFIED = "clarified"


class ReviewAction(Base):
    __tablename__ = "review_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_type = Column(String(20), nullable=False)
    extracted_item_id = Column(UUID(as_uuid=True), ForeignKey("extracted_items.id"), nullable=True)
    obligation_id = Column(UUID(as_uuid=True), ForeignKey("obligations.id"), nullable=True)
    previous_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    extracted_item = relationship("ExtractedItem", back_populates="review_actions")
    obligation = relationship("Obligation", back_populates="review_actions")
