from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base


class ClarificationQuestion(Base):
    __tablename__ = "clarification_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_version_id = Column(UUID(as_uuid=True), ForeignKey("contract_versions.id"), nullable=False)
    question = Column(Text, nullable=False)
    related_clauses = Column(ARRAY(String), nullable=True)
    context = Column(Text, nullable=True)
    source_sections = Column(ARRAY(String), nullable=True)
    source_pages = Column(ARRAY(Integer), nullable=True)
    source_quotes = Column(ARRAY(Text), nullable=True)
    answered = Column(String(10), default="false")  # "true" or "false"
    answer = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    contract_version = relationship("ContractVersion", back_populates="clarification_questions")
