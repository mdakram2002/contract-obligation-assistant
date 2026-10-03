from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base
from app.models.extracted_item import CertaintyLevel


class Ambiguity(Base):
    __tablename__ = "ambiguities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_version_id = Column(UUID(as_uuid=True), ForeignKey("contract_versions.id"), nullable=False)
    description = Column(Text, nullable=False)
    conflicting_clauses = Column(ARRAY(String), nullable=True)
    certainty = Column(String(20), default="low")
    source_sections = Column(ARRAY(String), nullable=True)
    source_pages = Column(ARRAY(Integer), nullable=True)
    source_quotes = Column(ARRAY(Text), nullable=True)
    notes = Column(Text, nullable=True)
    resolved = Column(String(10), default="false")  # "true" or "false"
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    contract_version = relationship("ContractVersion", back_populates="ambiguities")
