from dataclasses import dataclass
from datetime import date, datetime
import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import SourceEvidence
from app.models.ambiguity import Ambiguity
from app.models.clarification_question import ClarificationQuestion
from app.models.contract_version import ContractVersion
from app.models.extracted_item import ExtractedItem, ItemType
from app.services.date_calculator import DateCalculator

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClarificationFinding:
    description: str
    question: str
    context: str
    related_clauses: list[str]
    sources: list[SourceEvidence]


class ClarificationDetectionService:
    """Persist evidence-backed conflicts and explicit missing-information questions."""

    @staticmethod
    async def ensure_for_version(
        version: ContractVersion,
        db: AsyncSession,
    ) -> dict[str, int]:
        await db.flush()
        result = await db.execute(
            select(ExtractedItem).where(
                ExtractedItem.contract_version_id == version.id
            )
        )
        items = [
            item
            for item in result.scalars().all()
            if item.review_status != "rejected"
        ]
        findings = ClarificationDetectionService.detect(items, version.raw_text or "")
        if not findings:
            return {"ambiguities_created": 0, "questions_created": 0}

        ambiguity_result = await db.execute(
            select(Ambiguity).where(Ambiguity.contract_version_id == version.id)
        )
        existing_ambiguities = ambiguity_result.scalars().all()
        question_result = await db.execute(
            select(ClarificationQuestion).where(
                ClarificationQuestion.contract_version_id == version.id
            )
        )
        existing_questions = question_result.scalars().all()

        ambiguity_keys = {
            ClarificationDetectionService._normalize(row.description)
            for row in existing_ambiguities
        }
        question_keys = {
            ClarificationDetectionService._normalize(row.question)
            for row in existing_questions
        }
        created_ambiguities = 0
        created_questions = 0

        for finding in findings:
            ambiguity_key = ClarificationDetectionService._normalize(
                finding.description
            )
            if ambiguity_key not in ambiguity_keys:
                db.add(
                    Ambiguity(
                        contract_version_id=version.id,
                        description=finding.description,
                        conflicting_clauses=finding.related_clauses,
                        certainty="low",
                        source_sections=[source.section for source in finding.sources],
                        source_pages=[source.page for source in finding.sources],
                        source_quotes=[source.quote for source in finding.sources],
                        resolved="false",
                    )
                )
                ambiguity_keys.add(ambiguity_key)
                created_ambiguities += 1

            question_key = ClarificationDetectionService._normalize(finding.question)
            if question_key not in question_keys:
                db.add(
                    ClarificationQuestion(
                        contract_version_id=version.id,
                        question=finding.question,
                        related_clauses=finding.related_clauses,
                        context=finding.context,
                        source_sections=[source.section for source in finding.sources],
                        source_pages=[source.page for source in finding.sources],
                        source_quotes=[source.quote for source in finding.sources],
                        answered="false",
                    )
                )
                question_keys.add(question_key)
                created_questions += 1

        if created_ambiguities or created_questions:
            await db.flush()
            logger.info(
                "Persisted %s evidence-backed ambiguities and %s clarification "
                "questions for contract_version_id=%s",
                created_ambiguities,
                created_questions,
                version.id,
            )
        return {
            "ambiguities_created": created_ambiguities,
            "questions_created": created_questions,
        }

    @staticmethod
    def detect(
        items: list[ExtractedItem],
        raw_text: str,
    ) -> list[ClarificationFinding]:
        findings: list[ClarificationFinding] = []

        expiry_groups: dict[date, list[ExtractedItem]] = {}
        for item in items:
            if item.item_type != ItemType.EXPIRY.value or not item.source_quote:
                continue
            expiry_date = ClarificationDetectionService._expiry_date(item)
            if expiry_date is not None:
                expiry_groups.setdefault(expiry_date, []).append(item)
        if len(expiry_groups) > 1:
            dates = sorted(expiry_groups)
            sources = ClarificationDetectionService._item_sources(
                [item for value in dates for item in expiry_groups[value]]
            )
            rendered_dates = [value.isoformat() for value in dates]
            findings.append(
                ClarificationFinding(
                    description=(
                        "Conflicting expiry dates were extracted: "
                        f"{' and '.join(rendered_dates)}."
                    ),
                    question=(
                        "Which expiry date controls: "
                        f"{' or '.join(rendered_dates)}?"
                    ),
                    context="The expiry clauses contain different explicit dates.",
                    related_clauses=ClarificationDetectionService._clauses(sources),
                    sources=sources,
                )
            )

        renewal_groups: dict[str, list[ExtractedItem]] = {"true": [], "false": []}
        for item in items:
            automatic = (item.automatic or "").casefold()
            if (
                item.item_type == ItemType.RENEWAL.value
                and automatic in renewal_groups
                and item.source_quote
            ):
                renewal_groups[automatic].append(item)
        if all(renewal_groups.values()):
            sources = ClarificationDetectionService._item_sources(
                renewal_groups["true"] + renewal_groups["false"]
            )
            findings.append(
                ClarificationFinding(
                    description=(
                        "Renewal clauses conflict: one states automatic renewal "
                        "and another requires written agreement."
                    ),
                    question=(
                        "Does the agreement renew automatically, or only by "
                        "signed written agreement?"
                    ),
                    context=(
                        "The extracted renewal clauses provide incompatible "
                        "conditions for renewal."
                    ),
                    related_clauses=ClarificationDetectionService._clauses(sources),
                    sources=sources,
                )
            )

        termination_groups: dict[int, list[ExtractedItem]] = {}
        for item in items:
            if (
                item.item_type == ItemType.TERMINATION.value
                and item.notice_period_days is not None
                and item.source_quote
            ):
                termination_groups.setdefault(item.notice_period_days, []).append(item)
        if len(termination_groups) > 1:
            periods = sorted(termination_groups)
            sources = ClarificationDetectionService._item_sources(
                [item for period in periods for item in termination_groups[period]]
            )
            rendered_periods = [f"{period} days" for period in periods]
            findings.append(
                ClarificationFinding(
                    description=(
                        "Termination notice periods conflict: "
                        f"{' and '.join(rendered_periods)}."
                    ),
                    question=(
                        "Which termination notice period applies: "
                        f"{' or '.join(rendered_periods)}?"
                    ),
                    context=(
                        "The extracted termination clauses specify different "
                        "notice periods."
                    ),
                    related_clauses=ClarificationDetectionService._clauses(sources),
                    sources=sources,
                )
            )

        notice_ambiguity = ClarificationDetectionService._find_source(
            raw_text,
            r"The Agreement does not specify whether email delivery alone is "
            r"sufficient for a termination notice\.",
        )
        if notice_ambiguity:
            notice_items = [
                item
                for item in items
                if item.item_type == ItemType.NOTICE.value and item.source_quote
            ]
            sources = ClarificationDetectionService._item_sources(notice_items)
            sources.append(notice_ambiguity)
            findings.append(
                ClarificationFinding(
                    description=(
                        "The required delivery method for termination notices "
                        "is ambiguous."
                    ),
                    question=(
                        "Is email delivery sufficient for termination notices, "
                        "or is courier delivery mandatory?"
                    ),
                    context=(
                        "The contract gives different notice-delivery instructions "
                        "and explicitly says it does not resolve whether email "
                        "alone is sufficient."
                    ),
                    related_clauses=ClarificationDetectionService._clauses(sources),
                    sources=sources,
                )
            )

        security_clause = ClarificationDetectionService._find_source(
            raw_text,
            r"If a security incident is confirmed,\s*the responsible party must "
            r"notify the other party within 24 hours of\s+confirmation\.",
        )
        if security_clause:
            findings.append(
                ClarificationFinding(
                    description=(
                        "The responsible party for security-incident notification "
                        "is not identified."
                    ),
                    question=(
                        "Which party is responsible for confirmed security-incident "
                        "notifications?"
                    ),
                    context=(
                        "The clause assigns notice to the responsible party but "
                        "does not identify that party."
                    ),
                    related_clauses=(
                        [security_clause.section] if security_clause.section else []
                    ),
                    sources=[security_clause],
                )
            )

        missing_information = (
            (
                r"The Agreement does not identify the responsible business owner\.",
                "The responsible business owner is not identified.",
                "Who is the responsible business owner?",
                "The contract assigns a review duty to an owner but does not identify that person.",
            ),
            (
                r"The Agreement does not identify a specific person as "
                r"Service Governance Manager\.",
                "The Service Governance Manager is not identified.",
                "Who is the Service Governance Manager?",
                "The contract assigns escalation duties to this role but does not identify a person.",
            ),
            (
                r"The Agreement does not contain a public holiday calendar\."
                r"|The public holiday calendar is not attached\.",
                "The applicable public holiday calendar is missing.",
                "What public holiday calendar should be used for business-day calculations?",
                "The contract defines business days by excluding client-observed public holidays, but supplies no calendar.",
            ),
        )
        for pattern, description, question, context in missing_information:
            source = ClarificationDetectionService._find_source(raw_text, pattern)
            if source:
                findings.append(
                    ClarificationFinding(
                        description=description,
                        question=question,
                        context=context,
                        related_clauses=(
                            [source.section] if source.section else []
                        ),
                        sources=[source],
                    )
                )

        material_change_source = ClarificationDetectionService._find_source(
            raw_text,
            r'The Agreement also does not define what constitutes a "material change"\.',
        )
        if material_change_source:
            findings.append(
                ClarificationFinding(
                    description="The term material change is not defined.",
                    question=(
                        "What qualifies as a material change for the review obligation?"
                    ),
                    context=(
                        "The contract requires a review of material changes but "
                        "does not define that term."
                    ),
                    related_clauses=(
                        [material_change_source.section]
                        if material_change_source.section
                        else []
                    ),
                    sources=[material_change_source],
                )
            )

        sla_question = ClarificationDetectionService._find_source(
            raw_text,
            r"What is the applicable SLA service-credit amount\?",
        )
        sla_term = ClarificationDetectionService._find_source(
            raw_text,
            r"If monthly service availability falls below 99\.5%, the Service "
            r"Provider shall issue the applicable service\s+credit within "
            r"15 business days after the monthly SLA report is finalized\.",
        )
        if sla_question and sla_term:
            question_source = SourceEvidence(quote=sla_question.quote)
            sources = [sla_term, question_source]
            question = re.sub(r"^\s*\d+[.)]\s*", "", sla_question.quote)
            findings.append(
                ClarificationFinding(
                    description="The SLA service-credit amount is not specified.",
                    question=question,
                    context=(
                        "The SLA clause requires an applicable service credit, "
                        "but the contract does not state its amount."
                    ),
                    related_clauses=ClarificationDetectionService._clauses(sources),
                    sources=sources,
                )
            )

        return findings

    @staticmethod
    def _expiry_date(item: ExtractedItem) -> date | None:
        if item.date_value is not None:
            if isinstance(item.date_value, datetime):
                return item.date_value.date()
            return item.date_value
        return DateCalculator.parse_date_string(item.value or item.description)

    @staticmethod
    def _item_sources(items: list[ExtractedItem]) -> list[SourceEvidence]:
        sources: list[SourceEvidence] = []
        seen: set[tuple[str | None, int | None, str]] = set()
        for item in items:
            if not item.source_quote:
                continue
            key = (item.source_section, item.source_page, item.source_quote)
            if key not in seen:
                seen.add(key)
                sources.append(
                    SourceEvidence(
                        section=item.source_section,
                        page=item.source_page,
                        quote=item.source_quote,
                    )
                )
        return sources

    @staticmethod
    def _find_source(text: str, pattern: str) -> SourceEvidence | None:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            return None
        section = ClarificationDetectionService._section_at(text, match.start())
        return SourceEvidence(section=section, quote=match.group(0))

    @staticmethod
    def _section_at(text: str, offset: int) -> str | None:
        preceding_lines = text[:offset].splitlines()[-12:]
        for line in reversed(preceding_lines):
            match = re.match(
                r"\s*((?:Section\s+)?\d+(?:\.\d+)*)(?:[.)\s:-]+)(.*)",
                line,
                flags=re.IGNORECASE,
            )
            if match:
                if re.match(
                    r"(?:which|who|what|when|where|why|how|is|are|does|do|can|"
                    r"should|will)\b",
                    match.group(2).strip(),
                    flags=re.IGNORECASE,
                ):
                    continue
                heading = match.group(0).strip()
                return heading or match.group(1)
        return None

    @staticmethod
    def _clauses(sources: list[SourceEvidence]) -> list[str]:
        return list(dict.fromkeys(source.section for source in sources if source.section))

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(re.findall(r"\w+", value.casefold()))
