from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, date
from typing import Optional
import uuid
import json
import re
from app.models.contract_version import ContractVersion
from app.models.party import Party
from app.models.extracted_item import ExtractedItem, ItemType, ReviewStatus
from app.models.obligation import Obligation
from app.models.review_action import ReviewAction
from app.models.contract_extraction import ContractExtraction
from app.models.ambiguity import Ambiguity
from app.models.clarification_question import ClarificationQuestion
from app.models.ai_run import AIRun, AIRunStatus
from app.ai.schemas import ContractAnalysis, SourceEvidence
from app.services.contract_analyzer import ContractAnalyzer
from app.services.date_calculator import DateCalculator
from app.config import settings
import logging

logger = logging.getLogger(__name__)


def parse_date_string(date_str: Optional[str]) -> Optional[date]:
    """Parse date string to date object."""
    if date_str is None:
        return None
    if isinstance(date_str, date):
        return date_str
    return DateCalculator.parse_date_string(date_str)


def normalize_text(text: Optional[str]) -> str:
    """Normalize text for deduplication comparison."""
    if not text:
        return ""
    # Trim whitespace
    text = text.strip()
    # Normalize repeated spaces
    text = " ".join(text.split())
    return text


def get_item_dedup_key(
    contract_version_id: uuid.UUID,
    item_type: str,
    description: Optional[str] = None,
    value: Optional[str] = None,
    source_section: Optional[str] = None,
    source_quote: Optional[str] = None,
) -> str:
    """
    Create a content-based key that does not depend on section formatting.
    """
    kind = getattr(item_type, "value", item_type)
    if kind in (ItemType.EFFECTIVE_DATE.value, ItemType.EXPIRY.value) and normalize_text(value):
        content = _canonical_text(value)
    else:
        content = _canonical_text(source_quote) or _canonical_text(description) or _canonical_text(value)
    return json.dumps(
        [str(contract_version_id), kind, content],
        ensure_ascii=True,
    )


def _canonical_text(text: Optional[str]) -> str:
    if not text:
        return ""
    return " ".join(re.findall(r"\w+", text.casefold()))


def get_party_dedup_key(contract_version_id: uuid.UUID, name: str, role: Optional[str]) -> str:
    return json.dumps(
        [str(contract_version_id), _canonical_text(name), _canonical_text(role)],
        ensure_ascii=True,
    )


def get_obligation_dedup_key(
    contract_version_id: uuid.UUID,
    description: str,
    responsible_party: Optional[str],
    deadline: Optional[date] = None,
) -> str:
    return json.dumps(
        [
            str(contract_version_id),
            _canonical_text(description),
            _canonical_text(responsible_party),
            deadline.isoformat() if deadline else "",
        ],
        ensure_ascii=True,
    )


async def is_duplicate_item(
    contract_version_id: uuid.UUID,
    item_type: str,
    description: Optional[str] = None,
    value: Optional[str] = None,
    source_section: Optional[str] = None,
    db: AsyncSession = None
) -> bool:
    """
    Check if an item with the same normalized content already exists.
    """
    dedup_key = get_item_dedup_key(contract_version_id, item_type, description, value, source_section)

    # Check existing items
    result = await db.execute(
        select(ExtractedItem).where(ExtractedItem.contract_version_id == contract_version_id)
    )
    existing_items = result.scalars().all()

    for existing in existing_items:
        existing_key = get_item_dedup_key(
            contract_version_id,
            existing.item_type,
            existing.description,
            existing.value,
            existing.source_section
        )
        if existing_key == dedup_key:
            return True

    return False


async def is_duplicate_obligation(
    contract_version_id: uuid.UUID,
    description: str,
    responsible_party: Optional[str] = None,
    source_section: Optional[str] = None,
    db: AsyncSession = None
) -> bool:
    """
    Check if an obligation with the same normalized content already exists.
    Preserves distinct obligations that look similar but are different.
    """
    dedup_key = get_obligation_dedup_key(
        contract_version_id, description, responsible_party
    )

    # Check existing obligations
    result = await db.execute(
        select(Obligation).where(Obligation.contract_version_id == contract_version_id)
    )
    existing_obligations = result.scalars().all()

    for existing in existing_obligations:
        existing_key = get_obligation_dedup_key(
            contract_version_id,
            existing.description,
            existing.responsible_party,
            existing.deadline.date() if existing.deadline else None,
        )
        if existing_key == dedup_key:
            return True

    return False


async def is_duplicate_party(
    contract_version_id: uuid.UUID,
    name: str,
    role: Optional[str] = None,
    db: AsyncSession = None
) -> bool:
    """
    Check if a party with the same normalized name and role already exists.
    """
    dedup_key = get_party_dedup_key(contract_version_id, name, role)

    # Check existing parties
    result = await db.execute(
        select(Party).where(Party.contract_version_id == contract_version_id)
    )
    existing_parties = result.scalars().all()

    for existing in existing_parties:
        if get_party_dedup_key(contract_version_id, existing.name, existing.role) == dedup_key:
            return True

    return False


class AnalysisService:
    """Service to orchestrate contract analysis and database persistence."""

    def __init__(self):
        self.analyzer = ContractAnalyzer()

    async def analyze_contract_version(
        self,
        contract_version_id: uuid.UUID,
        db: AsyncSession
    ) -> dict:
        """
        Analyze a contract version and save results to database.
        Returns analysis summary with AI run ID.
        Idempotent: if extraction already exists for this version, returns existing data.
        """
        # Serialize analysis requests for this version on databases that support row locks.
        result = await db.execute(
            select(ContractVersion)
            .where(ContractVersion.id == contract_version_id)
            .with_for_update()
        )
        contract_version = result.scalar_one_or_none()
        if not contract_version:
            raise ValueError("Contract version not found")

        extraction_result = await db.execute(
            select(ContractExtraction).where(
                ContractExtraction.contract_version_id == contract_version_id
            )
        )
        extraction = extraction_result.scalar_one_or_none()
        if extraction and extraction.status == "completed":
            return {
                "ai_run_id": extraction.ai_run_id,
                "status": "already_exists",
                "duration_ms": 0
            }

        if extraction is None:
            extraction = ContractExtraction(
                contract_version_id=contract_version_id,
                status="started",
            )
            db.add(extraction)
            await db.flush()
        else:
            extraction.status = "started"
            extraction.completed_at = None

        # Older installations have extracted records but no extraction marker.
        existing_data = await self._load_existing_data(contract_version_id, db)
        ai_run_result = await db.execute(
            select(AIRun)
            .where(AIRun.contract_version_id == contract_version_id)
            .where(AIRun.status == AIRunStatus.COMPLETED)
            .order_by(AIRun.created_at.desc())
            .limit(1)
        )
        ai_run = ai_run_result.scalar_one_or_none()
        if any(existing_data.values()) or ai_run:
            await self._deduplicate_existing_data(contract_version_id, existing_data, db)
            extraction.status = "completed"
            extraction.ai_run_id = ai_run.id if ai_run else None
            extraction.completed_at = datetime.utcnow()
            await db.commit()
            logger.info(
                "Existing extraction reused for contract_version_id=%s",
                contract_version_id,
            )
            return {
                "ai_run_id": extraction.ai_run_id,
                "status": "already_exists",
                "duration_ms": 0,
            }

        # Create AI run record
        run_id = str(uuid.uuid4())
        ai_run = AIRun(
            contract_version_id=contract_version_id,
            run_id=run_id,
            provider="groq",
            model=settings.GROQ_MODEL,
            status=AIRunStatus.STARTED
        )
        db.add(ai_run)
        await db.flush()
        extraction.ai_run_id = ai_run.id

        start_time = datetime.utcnow()

        try:
            # Analyze contract
            logger.info(f"Starting analysis for contract_version_id={contract_version_id}")
            analysis: ContractAnalysis = await self.analyzer.analyze(contract_version.raw_text)

            party_keys = set()
            item_keys = set()
            obligation_keys = set()

            # Save parties
            for party_data in analysis.parties:
                key = get_party_dedup_key(
                    contract_version_id, party_data.name, party_data.role
                )
                if key not in party_keys:
                    party_keys.add(key)
                    party = Party(
                        contract_version_id=contract_version_id,
                        name=party_data.name,
                        role=party_data.role,
                        source_section=party_data.source.section,
                        source_page=party_data.source.page,
                        source_quote=party_data.source.quote
                    )
                    db.add(party)

            # Save effective date as an extracted item
            effective_date_value = parse_date_string(analysis.effective_date.date)
            effective_date_item = self._create_extracted_item(
                contract_version_id,
                ItemType.EFFECTIVE_DATE,
                "Effective Date",
                value=analysis.effective_date.date,
                date_value=effective_date_value,
                certainty=analysis.effective_date.certainty,
                source=analysis.effective_date.source,
                notes=analysis.effective_date.notes,
            )
            self._add_extracted_item(effective_date_item, item_keys, db)

            # Save expiry clauses
            for expiry in analysis.expiry_clauses:
                expiry_date_value = parse_date_string(expiry.date)
                item = self._create_extracted_item(
                    contract_version_id,
                    ItemType.EXPIRY,
                    "Expiry Clause",
                    value=expiry.date,
                    date_value=expiry_date_value,
                    description=expiry.description,
                    certainty=expiry.certainty,
                    source=expiry.source,
                    notes=expiry.notes,
                )
                self._add_extracted_item(item, item_keys, db)

            # Save renewal terms
            for renewal in analysis.renewal_terms:
                item = self._create_extracted_item(
                    contract_version_id,
                    ItemType.RENEWAL,
                    "Renewal Term",
                    description=renewal.description,
                    notice_period_days=renewal.notice_period_days,
                    automatic="true" if renewal.automatic else "false" if renewal.automatic is False else None,
                    certainty=renewal.certainty,
                    source=renewal.source,
                    notes=renewal.notes,
                )
                self._add_extracted_item(item, item_keys, db)

            # Save termination terms (with deduplication)
            for termination in analysis.termination_terms:
                item = self._create_extracted_item(
                    contract_version_id,
                    ItemType.TERMINATION,
                    "Termination Term",
                    description=termination.description,
                    notice_period_days=termination.notice_period_days,
                    conditions=termination.conditions,
                    certainty=termination.certainty,
                    source=termination.source,
                    notes=termination.notes,
                )
                self._add_extracted_item(item, item_keys, db)

            # Save notice terms (with deduplication)
            for notice in analysis.notice_terms:
                item = self._create_extracted_item(
                    contract_version_id,
                    ItemType.NOTICE,
                    "Notice Term",
                    description=notice.description,
                    notice_period_days=notice.notice_period_days,
                    purpose=notice.purpose,
                    certainty=notice.certainty,
                    source=notice.source,
                    notes=notice.notes,
                )
                self._add_extracted_item(item, item_keys, db)

            # Save obligations (with deduplication)
            for obligation in analysis.obligations:
                obligation_deadline = parse_date_string(obligation.deadline)
                key = get_obligation_dedup_key(
                    contract_version_id,
                    obligation.description,
                    obligation.responsible_party,
                    obligation_deadline,
                )
                if key not in obligation_keys:
                    obligation_keys.add(key)
                    obligation_db = Obligation(
                        contract_version_id=contract_version_id,
                        description=obligation.description,
                        responsible_party=obligation.responsible_party,
                        deadline=obligation_deadline,
                        deadline_description=obligation.deadline_description,
                        certainty=obligation.certainty,
                        source_section=obligation.source.section,
                        source_page=obligation.source.page,
                        source_quote=obligation.source.quote,
                        notes=obligation.notes,
                        review_status=ReviewStatus.PENDING
                    )
                    db.add(obligation_db)

            # Save ambiguities
            if analysis.ambiguities:
                for ambiguity in analysis.ambiguities:
                    ambiguity_db = Ambiguity(
                        contract_version_id=contract_version_id,
                        description=ambiguity.description,
                        conflicting_clauses=ambiguity.conflicting_clauses,
                        certainty=ambiguity.certainty,
                        source_sections=[s.section for s in ambiguity.source],
                        source_pages=[s.page for s in ambiguity.source],
                        source_quotes=[s.quote for s in ambiguity.source],
                        notes=ambiguity.notes,
                        resolved="false"
                    )
                    db.add(ambiguity_db)

            # Save clarification questions
            if analysis.clarification_questions:
                for question in analysis.clarification_questions:
                    question_db = ClarificationQuestion(
                        contract_version_id=contract_version_id,
                        question=question.question,
                        related_clauses=question.related_clauses,
                        context=question.context,
                        source_sections=[s.section for s in question.source],
                        source_pages=[s.page for s in question.source],
                        source_quotes=[s.quote for s in question.source],
                        answered="false"
                    )
                    db.add(question_db)

            # Update AI run record
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            ai_run.status = AIRunStatus.COMPLETED
            ai_run.duration_ms = duration_ms
            ai_run.validation_result = "passed"
            ai_run.completed_at = end_time
            extraction.status = "completed"
            extraction.completed_at = end_time

            await db.commit()
            await db.refresh(ai_run)

            logger.info(f"Analysis completed for contract_version_id={contract_version_id}, duration={duration_ms}ms")

            return {
                "ai_run_id": ai_run.id,
                "status": "completed",
                "duration_ms": duration_ms
            }

        except Exception as e:
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            await db.rollback()
            failed_run = AIRun(
                contract_version_id=contract_version_id,
                run_id=run_id,
                provider="groq",
                model=settings.GROQ_MODEL,
                status=AIRunStatus.FAILED,
                duration_ms=duration_ms,
                validation_result="failed",
                error_message=str(e),
                completed_at=end_time,
            )
            db.add(failed_run)
            await db.flush()
            failed_extraction = ContractExtraction(
                contract_version_id=contract_version_id,
                status="failed",
                ai_run_id=failed_run.id,
            )
            db.add(failed_extraction)
            await db.commit()

            logger.error(f"Analysis failed for contract_version_id={contract_version_id}: {str(e)}")
            raise

    @staticmethod
    async def _load_existing_data(contract_version_id: uuid.UUID, db: AsyncSession) -> dict:
        models = {
            "parties": Party,
            "items": ExtractedItem,
            "obligations": Obligation,
        }
        existing = {}
        for key, model in models.items():
            result = await db.execute(
                select(model).where(model.contract_version_id == contract_version_id)
            )
            existing[key] = result.scalars().all()
        return existing

    @staticmethod
    async def _deduplicate_existing_data(
        contract_version_id: uuid.UUID,
        existing_data: dict,
        db: AsyncSession,
    ) -> None:
        def choose_keeper(records):
            return max(
                records,
                key=lambda record: (
                    record.user_edited == "true",
                    record.review_status in ("approved", "rejected", "needs_clarification"),
                    bool(record.source_quote),
                    record.updated_at or record.created_at,
                ),
            )

        party_groups = {}
        for party in existing_data["parties"]:
            key = get_party_dedup_key(contract_version_id, party.name, party.role)
            party_groups.setdefault(key, []).append(party)

        item_groups = {}
        for item in existing_data["items"]:
            key = get_item_dedup_key(
                contract_version_id,
                item.item_type,
                item.description,
                item.value,
                item.source_section,
                item.source_quote,
            )
            item_groups.setdefault(key, []).append(item)

        obligation_groups = {}
        for obligation in existing_data["obligations"]:
            key = get_obligation_dedup_key(
                contract_version_id,
                obligation.description,
                obligation.responsible_party,
                obligation.deadline.date() if obligation.deadline else None,
            )
            obligation_groups.setdefault(key, []).append(obligation)

        for groups, action_field in (
            (item_groups, ReviewAction.extracted_item_id),
            (obligation_groups, ReviewAction.obligation_id),
        ):
            for records in groups.values():
                if len(records) < 2:
                    continue
                keeper = choose_keeper(records)
                duplicate_ids = [record.id for record in records if record.id != keeper.id]
                await db.execute(
                    ReviewAction.__table__.update()
                    .where(action_field.in_(duplicate_ids))
                    .values({action_field.key: keeper.id})
                )
                keeper.user_edited = (
                    "true" if any(record.user_edited == "true" for record in records) else "false"
                )
                if keeper.review_status == "pending":
                    keeper.review_status = next(
                        (
                            record.review_status
                            for record in records
                            if record.review_status in ("approved", "rejected", "needs_clarification")
                        ),
                        keeper.review_status,
                    )
                if not keeper.source_quote:
                    keeper.source_quote = next(
                        (record.source_quote for record in records if record.source_quote), None
                    )
                if not keeper.source_section:
                    keeper.source_section = next(
                        (record.source_section for record in records if record.source_section), None
                    )
                if not keeper.source_page:
                    keeper.source_page = next(
                        (record.source_page for record in records if record.source_page is not None), None
                    )
                for record in records:
                    if record.id != keeper.id:
                        await db.delete(record)

        for records in party_groups.values():
            if len(records) < 2:
                continue
            keeper = max(
                records,
                key=lambda record: (
                    bool(record.source_quote),
                    record.created_at,
                ),
            )
            for record in records:
                if record.id != keeper.id:
                    await db.delete(record)

    @staticmethod
    def _create_extracted_item(
        contract_version_id,
        item_type,
        title,
        source: SourceEvidence,
        **fields,
    ) -> ExtractedItem:
        return ExtractedItem(
            contract_version_id=contract_version_id,
            item_type=item_type,
            title=title,
            source_section=source.section,
            source_page=source.page,
            source_quote=source.quote,
            review_status=ReviewStatus.PENDING,
            **fields,
        )

    @staticmethod
    def _add_extracted_item(item, seen_keys: set, db: AsyncSession) -> None:
        key = get_item_dedup_key(
            item.contract_version_id,
            item.item_type,
            item.description,
            item.value,
            item.source_section,
            item.source_quote,
        )
        if key not in seen_keys:
            seen_keys.add(key)
            db.add(item)
