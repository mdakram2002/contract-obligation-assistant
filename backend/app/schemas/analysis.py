from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, List
from uuid import UUID


class SourceEvidenceResponse(BaseModel):
    section: Optional[str] = None
    page: Optional[int] = None
    quote: str


class PartyResponse(BaseModel):
    id: UUID
    name: str
    role: Optional[str] = None
    source_section: Optional[str] = None
    source_page: Optional[int] = None
    source_quote: Optional[str] = None

    class Config:
        from_attributes = True


class ExtractedItemResponse(BaseModel):
    id: UUID
    item_type: str
    title: str
    value: Optional[str] = None
    date_value: Optional[datetime] = None
    notice_period_days: Optional[int] = None
    description: Optional[str] = None
    conditions: Optional[str] = None
    purpose: Optional[str] = None
    automatic: Optional[str] = None
    certainty: str
    source_section: Optional[str] = None
    source_page: Optional[int] = None
    source_quote: Optional[str] = None
    notes: Optional[str] = None
    review_status: str
    is_stale: str
    user_edited: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ObligationResponse(BaseModel):
    id: UUID
    description: str
    responsible_party: Optional[str] = None
    deadline: Optional[datetime] = None
    deadline_description: Optional[str] = None
    certainty: str
    source_section: Optional[str] = None
    source_page: Optional[int] = None
    source_quote: Optional[str] = None
    notes: Optional[str] = None
    review_status: str
    is_stale: str
    user_edited: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AmbiguityResponse(BaseModel):
    id: UUID
    description: str
    conflicting_clauses: Optional[List[str]] = None
    certainty: str
    source_sections: Optional[List[str]] = None
    source_pages: Optional[List[Optional[int]]] = None
    source_quotes: Optional[List[str]] = None
    notes: Optional[str] = None
    resolved: str
    created_at: datetime

    class Config:
        from_attributes = False


class ClarificationQuestionResponse(BaseModel):
    id: UUID
    question: str
    related_clauses: Optional[List[str]] = None
    context: Optional[str] = None
    source_sections: Optional[List[str]] = None
    source_pages: Optional[List[Optional[int]]] = None
    source_quotes: Optional[List[str]] = None
    answered: str
    answer: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = False


class AnalysisResponse(BaseModel):
    contract_version_id: UUID
    parties: List[PartyResponse]
    extracted_items: List[ExtractedItemResponse]
    obligations: List[ObligationResponse]
    ambiguities: List[AmbiguityResponse]
    clarification_questions: List[ClarificationQuestionResponse]
    ai_run_id: Optional[UUID] = None
    analysis_status: str


class AnalysisRequest(BaseModel):
    contract_version_id: str
