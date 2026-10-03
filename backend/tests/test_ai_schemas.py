import pytest
from app.ai.schemas import (
    ContractAnalysisResult,
    PartyInfo,
    ExtractedItemInfo,
    ObligationInfo,
    AmbiguityInfo,
    ClarificationQuestionInfo,
    SourceEvidence
)


class TestAISchemas:
    """Tests for AI output schema validation."""

    def test_source_evidence_valid(self):
        """Test valid source evidence schema."""
        evidence = SourceEvidence(
            section="12.2",
            page=8,
            quote="Customer shall provide notice within 90 days"
        )
        assert evidence.section == "12.2"
        assert evidence.page == 8
        assert evidence.quote == "Customer shall provide notice within 90 days"

    def test_source_evidence_optional_fields(self):
        """Test source evidence with optional fields."""
        evidence = SourceEvidence(
            section="12.2",
            page=None,
            quote="Some text"
        )
        assert evidence.section == "12.2"
        assert evidence.page is None
        assert evidence.quote == "Some text"

    def test_party_info_valid(self):
        """Test valid party info schema."""
        party = PartyInfo(
            name="ABC Corporation",
            role="Service Provider",
            source_evidence=SourceEvidence(
                section="1",
                page=1,
                quote="ABC Corporation ('Service Provider')"
            )
        )
        assert party.name == "ABC Corporation"
        assert party.role == "Service Provider"
        assert party.source_evidence.section == "1"

    def test_extracted_item_info_valid(self):
        """Test valid extracted item info schema."""
        item = ExtractedItemInfo(
            item_type="expiry",
            title="Contract Expiry Date",
            value="December 31, 2028",
            certainty="high",
            source_evidence=SourceEvidence(
                section="2.1",
                page=2,
                quote="The Agreement shall expire on December 31, 2028"
            )
        )
        assert item.item_type == "expiry"
        assert item.title == "Contract Expiry Date"
        assert item.certainty == "high"

    def test_obligation_info_valid(self):
        """Test valid obligation info schema."""
        obligation = ObligationInfo(
            description="Provide monthly status reports",
            responsible_party="Service Provider",
            deadline="2026-02-05",
            certainty="high",
            source_evidence=SourceEvidence(
                section="5.1(c)",
                page=4,
                quote="Provide monthly status reports to Client by the fifth business day"
            )
        )
        assert obligation.description == "Provide monthly status reports"
        assert obligation.responsible_party == "Service Provider"
        assert obligation.deadline == "2026-02-05"

    def test_ambiguity_info_valid(self):
        """Test valid ambiguity info schema."""
        ambiguity = AmbiguityInfo(
            description="Conflicting notice periods in different sections",
            conflicting_clauses=["Section 2.2: 30 days", "Section 2.3: 90 days"],
            certainty="high",
            source_sections=["2.2", "2.3"],
            source_pages=[2, 2]
        )
        assert ambiguity.description == "Conflicting notice periods"
        assert len(ambiguity.conflicting_clauses) == 2
        assert ambiguity.certainty == "high"

    def test_clarification_question_info_valid(self):
        """Test valid clarification question info schema."""
        question = ClarificationQuestionInfo(
            question="Which notice period should apply - 30 days or 90 days?",
            related_clauses=["Section 2.2", "Section 2.3"],
            context="Both sections specify different notice periods for termination",
            source_sections=["2.2", "2.3"]
        )
        assert question.question == "Which notice period should apply"
        assert len(question.related_clauses) == 2

    def test_contract_analysis_result_valid(self):
        """Test valid contract analysis result schema."""
        analysis = ContractAnalysisResult(
            parties=[
                PartyInfo(
                    name="ABC Corporation",
                    role="Service Provider",
                    source_evidence=SourceEvidence(section="1", page=1, quote="ABC Corp")
                )
            ],
            effective_date={
                "value": "January 1, 2026",
                "certainty": "high",
                "source_evidence": SourceEvidence(section="1", page=1, quote="Effective Date")
            },
            expiry={
                "value": "December 31, 2028",
                "certainty": "high",
                "source_evidence": SourceEvidence(section="2.1", page=2, quote="expires on")
            },
            renewal_terms=[
                ExtractedItemInfo(
                    item_type="renewal",
                    title="Automatic Renewal",
                    value="1 year terms",
                    certainty="high",
                    source_evidence=SourceEvidence(section="3.1", page=3, quote="automatically renew")
                )
            ],
            termination_terms=[
                ExtractedItemInfo(
                    item_type="termination",
                    title="Termination for Cause",
                    value="30 days notice",
                    certainty="high",
                    source_evidence=SourceEvidence(section="2.2", page=2, quote="30 days written notice")
                )
            ],
            notice_terms=[
                ExtractedItemInfo(
                    item_type="notice",
                    title="Notice Period",
                    value="30 days",
                    notice_period_days=30,
                    certainty="high",
                    source_evidence=SourceEvidence(section="2.2", page=2, quote="30 days")
                )
            ],
            obligations=[
                ObligationInfo(
                    description="Provide monthly status reports",
                    responsible_party="Service Provider",
                    deadline="2026-02-05",
                    certainty="high",
                    source_evidence=SourceEvidence(section="5.1", page=4, quote="monthly status reports")
                )
            ],
            ambiguities=[],
            clarification_questions=[]
        )
        assert len(analysis.parties) == 1
        assert analysis.effective_date["value"] == "January 1, 2026"
        assert len(analysis.obligations) == 1

    def test_contract_analysis_result_minimal(self):
        """Test contract analysis result with minimal required fields."""
        analysis = ContractAnalysisResult(
            parties=[],
            effective_date=None,
            expiry=None,
            renewal_terms=[],
            termination_terms=[],
            notice_terms=[],
            obligations=[],
            ambiguities=[],
            clarification_questions=[]
        )
        assert len(analysis.parties) == 0
        assert analysis.effective_date is None
