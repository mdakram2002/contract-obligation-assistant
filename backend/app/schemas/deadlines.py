from pydantic import BaseModel, Field
from datetime import date
from typing import Optional
from uuid import UUID


class UndatedObligationResponse(BaseModel):
    id: UUID
    description: str
    timing_description: Optional[str] = None
    timing_kind: str
    source_section: Optional[str] = None
    source_quote: Optional[str] = None
    certainty: str
    review_status: str


class DeadlineResponse(BaseModel):
    id: UUID
    description: str
    deadline: date
    days_remaining: int
    type: str  # "notice", "renewal", "termination", "obligation"
    source_section: Optional[str] = None
    certainty: str
    review_status: str


class UpcomingDeadlinesResponse(BaseModel):
    deadlines: list[DeadlineResponse]
    total: int
    undated_obligations: list[UndatedObligationResponse] = Field(default_factory=list)


class DeadlineCalculationRequest(BaseModel):
    contract_version_id: str
    contract_id: Optional[str] = None
