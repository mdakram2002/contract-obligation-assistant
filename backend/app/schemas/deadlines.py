from pydantic import BaseModel
from datetime import date
from typing import Optional
from uuid import UUID


class DeadlineResponse(BaseModel):
    id: UUID
    description: str
    deadline: date
    days_remaining: int
    type: str  # "notice", "renewal", "termination", "obligation"
    source_section: Optional[str] = None
    certainty: str


class UpcomingDeadlinesResponse(BaseModel):
    deadlines: list[DeadlineResponse]
    total: int


class DeadlineCalculationRequest(BaseModel):
    contract_version_id: str
    contract_id: Optional[str] = None
