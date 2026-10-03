from datetime import datetime
from types import SimpleNamespace
import uuid

import pytest
from pydantic import ValidationError

from app.ai.schemas import ContractAnalysis
from app.schemas.analysis import AmbiguityResponse, ClarificationQuestionResponse


def base_analysis():
    return {
        "parties": [],
        "effective_date": {
            "date": None,
            "certainty": "low",
            "source": {
                "section": "Preamble",
                "quote": "The effective date is not stated.",
            },
        },
        "expiry_clauses": [],
        "renewal_terms": [],
        "termination_terms": [],
    }


def test_notice_terms_and_obligations_default_to_empty_lists():
    analysis = ContractAnalysis.model_validate(base_analysis())

    assert analysis.notice_terms == []
    assert analysis.obligations == []


def test_analysis_preserves_conflicting_dates_and_evidence():
    payload = base_analysis()
    payload["expiry_clauses"] = [
        {
            "date": "2027-10-14",
            "description": "Expiry date in term section",
            "certainty": "low",
            "source": {"section": "2.1", "quote": "The term ends October 14, 2027."},
        },
        {
            "date": "2027-10-15",
            "description": "Expiry date in schedule",
            "certainty": "low",
            "source": {"section": "Schedule A", "quote": "Expiry: October 15, 2027."},
        },
    ]

    analysis = ContractAnalysis.model_validate(payload)

    assert [item.date for item in analysis.expiry_clauses] == [
        "2027-10-14",
        "2027-10-15",
    ]
    assert [item.source.quote for item in analysis.expiry_clauses] == [
        "The term ends October 14, 2027.",
        "Expiry: October 15, 2027.",
    ]


def test_analysis_rejects_invalid_certainty():
    payload = base_analysis()
    payload["effective_date"]["certainty"] = "certain"

    with pytest.raises(ValidationError):
        ContractAnalysis.model_validate(payload)


def test_clarification_responses_allow_unknown_source_sections():
    shared = {
        "id": uuid.uuid4(),
        "contract_version_id": uuid.uuid4(),
        "source_sections": ["9. SLA CREDIT", None],
        "source_pages": [9, None],
        "source_quotes": [
            "The applicable service credit is due after the report.",
            "What is the applicable SLA service-credit amount?",
        ],
        "created_at": datetime(2026, 10, 3),
    }

    ambiguity = AmbiguityResponse.model_validate(
        SimpleNamespace(
            **shared,
            description="The SLA service-credit amount is not specified.",
            conflicting_clauses=["9. SLA CREDIT"],
            certainty="low",
            notes=None,
            resolved="false",
        )
    )
    question = ClarificationQuestionResponse.model_validate(
        SimpleNamespace(
            **shared,
            question="What is the applicable SLA service-credit amount?",
            related_clauses=["9. SLA CREDIT"],
            context="The amount is not stated.",
            answered="false",
            answer=None,
        )
    )

    assert ambiguity.source_sections == ["9. SLA CREDIT", None]
    assert question.source_sections == ["9. SLA CREDIT", None]
