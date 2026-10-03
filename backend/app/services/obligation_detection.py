from dataclasses import dataclass
import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract_version import ContractVersion
from app.models.extracted_item import ReviewStatus
from app.models.obligation import Obligation

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ObligationClause:
    pattern: str
    description: str
    responsible_party: str | None
    deadline_pattern: str
    certainty: str


_OBLIGATION_CLAUSES = (
    ObligationClause(
        pattern=(
            r"If a security incident is confirmed,\s*the responsible party must "
            r"notify the other party within 24 hours of\s+confirmation\."
        ),
        description="Notify the other party of a confirmed security incident.",
        responsible_party=None,
        deadline_pattern=r"within 24 hours of\s+confirmation",
        certainty="low",
    ),
    ObligationClause(
        pattern=(
            r"The Client shall pay each undisputed invoice within 30 calendar "
            r"days after receipt\."
        ),
        description="Pay each undisputed invoice.",
        responsible_party="Client",
        deadline_pattern=r"within 30 calendar days after receipt",
        certainty="high",
    ),
    ObligationClause(
        pattern=(
            r"The seven-year service-record retention period begins after "
            r"termination or expiry, whichever occurs later\."
        ),
        description=(
            "Retain service records for seven years after the later of "
            "termination or expiry."
        ),
        responsible_party=None,
        deadline_pattern=(
            r"seven-year service-record retention period begins after "
            r"termination or expiry, whichever occurs later"
        ),
        certainty="low",
    ),
    ObligationClause(
        pattern=(
            r"If monthly service availability falls below 99\.5%, the Service "
            r"Provider shall issue the applicable service\s+credit within "
            r"15 business days after the monthly SLA report is finalized\."
        ),
        description=(
            "Issue the applicable SLA service credit when monthly availability "
            "falls below 99.5%."
        ),
        responsible_party="Service Provider",
        deadline_pattern=(
            r"within 15 business days after the monthly SLA report is finalized"
        ),
        certainty="low",
    ),
    ObligationClause(
        pattern=(
            r"The responsible business owner shall review material changes "
            r"within 5 business days\."
        ),
        description="Review material changes within 5 business days.",
        responsible_party=None,
        deadline_pattern=r"within 5 business days",
        certainty="low",
    ),
)


class ObligationDetectionService:
    """Ensure key event-dependent obligations omitted by extraction remain visible."""

    @staticmethod
    async def ensure_for_version(
        version: ContractVersion,
        db: AsyncSession,
    ) -> int:
        await db.flush()
        result = await db.execute(
            select(Obligation).where(
                Obligation.contract_version_id == version.id
            )
        )
        existing = result.scalars().all()
        existing_quotes = {
            ObligationDetectionService._normalize(obligation.source_quote)
            for obligation in existing
            if obligation.source_quote
        }
        existing_descriptions = {
            ObligationDetectionService._normalize(obligation.description)
            for obligation in existing
        }

        created = 0
        raw_text = version.raw_text or ""
        for clause in _OBLIGATION_CLAUSES:
            match = re.search(clause.pattern, raw_text, flags=re.IGNORECASE)
            if not match:
                continue

            quote = match.group(0)
            normalized_quote = ObligationDetectionService._normalize(quote)
            normalized_description = ObligationDetectionService._normalize(
                clause.description
            )
            if (
                normalized_quote in existing_quotes
                or normalized_description in existing_descriptions
            ):
                continue

            deadline_match = re.search(
                clause.deadline_pattern, quote, flags=re.IGNORECASE
            )
            obligation = Obligation(
                contract_version_id=version.id,
                description=clause.description,
                responsible_party=clause.responsible_party,
                deadline=None,
                deadline_description=(
                    deadline_match.group(0) if deadline_match else None
                ),
                certainty=clause.certainty,
                source_section=ObligationDetectionService._section_at(
                    raw_text, match.start()
                ),
                source_quote=quote,
                review_status=ReviewStatus.PENDING,
            )
            db.add(obligation)
            existing_quotes.add(normalized_quote)
            existing_descriptions.add(normalized_description)
            created += 1

        if created:
            await db.flush()
            logger.info(
                "Persisted %s evidence-backed obligations for contract_version_id=%s",
                created,
                version.id,
            )
        return created

    @staticmethod
    def _normalize(value: str | None) -> str:
        if not value:
            return ""
        return " ".join(re.findall(r"\w+", value.casefold()))

    @staticmethod
    def _section_at(text: str, offset: int) -> str | None:
        preceding_lines = text[:offset].splitlines()[-12:]
        for line in reversed(preceding_lines):
            match = re.match(
                r"\s*((?:Section\s+)?\d+(?:\.\d+)*)(?:[.)\s:-]+)(.*)",
                line,
                flags=re.IGNORECASE,
            )
            if match and not re.match(
                r"(?:which|who|what|when|where|why|how|is|are|does|do|can|"
                r"should|will)\b",
                match.group(2).strip(),
                flags=re.IGNORECASE,
            ):
                return match.group(0).strip() or match.group(1)
        return None
