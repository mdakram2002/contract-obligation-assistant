from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date
from enum import Enum


class CertaintyLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceEvidence(BaseModel):
    section: Optional[str] = None
    page: Optional[int] = None
    quote: str


class Party(BaseModel):
    name: str
    role: Optional[str] = None
    source: SourceEvidence


class EffectiveDate(BaseModel):
    date: Optional[str] = None
    certainty: CertaintyLevel
    source: SourceEvidence
    notes: Optional[str] = None


class ExpiryClause(BaseModel):
    date: Optional[str] = None
    description: str
    certainty: CertaintyLevel
    source: SourceEvidence
    notes: Optional[str] = None


class RenewalTerm(BaseModel):
    description: str
    notice_period_days: Optional[int] = None
    automatic: Optional[bool] = None
    certainty: CertaintyLevel
    source: SourceEvidence
    notes: Optional[str] = None


class TerminationTerm(BaseModel):
    description: str
    notice_period_days: Optional[int] = None
    conditions: Optional[str] = None
    certainty: CertaintyLevel
    source: SourceEvidence
    notes: Optional[str] = None


class NoticeTerm(BaseModel):
    description: str
    notice_period_days: Optional[int] = None
    purpose: Optional[str] = None
    certainty: CertaintyLevel
    source: SourceEvidence
    notes: Optional[str] = None


class Obligation(BaseModel):
    description: str
    responsible_party: Optional[str] = None
    deadline: Optional[str] = None
    deadline_description: Optional[str] = None
    certainty: CertaintyLevel
    source: SourceEvidence
    notes: Optional[str] = None


class Ambiguity(BaseModel):
    description: str
    conflicting_clauses: List[str]
    certainty: CertaintyLevel
    source: List[SourceEvidence]
    notes: Optional[str] = None


class ClarificationQuestion(BaseModel):
    question: str
    related_clauses: List[str]
    context: str
    source: List[SourceEvidence]


class ContractAnalysis(BaseModel):
    parties: List[Party]
    effective_date: EffectiveDate
    expiry_clauses: List[ExpiryClause]
    renewal_terms: List[RenewalTerm]
    termination_terms: List[TerminationTerm]
    notice_terms: List[NoticeTerm]
    obligations: List[Obligation]
    ambiguities: Optional[List[Ambiguity]] = []
    clarification_questions: Optional[List[ClarificationQuestion]] = []
