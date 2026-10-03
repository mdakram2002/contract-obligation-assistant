from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.database import Base


class ContractExtraction(Base):
    __tablename__ = "contract_extractions"

    contract_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contract_versions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    status = Column(String(20), nullable=False, default="started")
    ai_run_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
