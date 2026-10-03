from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base


class ContractVersion(Base):
    __tablename__ = "contract_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    file_name = Column(String(255), nullable=True)
    file_type = Column(String(50), nullable=True)  # pdf, docx, text
    raw_text = Column(Text, nullable=False)
    parsing_metadata = Column(JSON, nullable=True)  # Document parsing metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    contract = relationship("Contract", back_populates="versions")
    parties = relationship("Party", back_populates="contract_version", cascade="all, delete-orphan")
    extracted_items = relationship("ExtractedItem", back_populates="contract_version", cascade="all, delete-orphan")
    obligations = relationship("Obligation", back_populates="contract_version", cascade="all, delete-orphan")
    ambiguities = relationship("Ambiguity", back_populates="contract_version", cascade="all, delete-orphan")
    clarification_questions = relationship("ClarificationQuestion", back_populates="contract_version", cascade="all, delete-orphan")
    ai_runs = relationship("AIRun", back_populates="contract_version", cascade="all, delete-orphan")
