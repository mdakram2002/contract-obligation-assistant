from datetime import date, datetime, timedelta
import logging
import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract_version import ContractVersion
from app.models.extracted_item import ExtractedItem, ItemType
from app.models.obligation import Obligation
from app.schemas.deadlines import (
    DeadlineResponse,
    UndatedObligationResponse,
    UpcomingDeadlinesResponse,
)
from app.services.date_calculator import DateCalculator

logger = logging.getLogger(__name__)


class DeadlineService:
    """Derive upcoming dates only from explicit dates or dated contract terms."""

    @staticmethod
    async def calculate_for_version(
        contract_version_id: uuid.UUID,
        days_ahead: int,
        db: AsyncSession,
        contract_id: uuid.UUID | None = None,
        today: date | None = None,
    ) -> UpcomingDeadlinesResponse:
        if not 1 <= days_ahead <= 365:
            raise ValueError("days_ahead must be between 1 and 365")

        version_query = select(ContractVersion).where(
            ContractVersion.id == contract_version_id
        )
        if contract_id is not None:
            version_query = version_query.where(
                ContractVersion.contract_id == contract_id
            )
        version = (await db.execute(version_query)).scalar_one_or_none()
        if version is None:
            raise ValueError("Contract version not found for selected contract")

        item_result = await db.execute(
            select(ExtractedItem).where(
                ExtractedItem.contract_version_id == contract_version_id
            )
        )
        items = [
            item
            for item in item_result.scalars().all()
            if item.review_status != "rejected" and item.is_stale != "true"
        ]

        obligation_result = await db.execute(
            select(Obligation).where(
                Obligation.contract_version_id == contract_version_id
            )
        )
        obligations = [
            obligation
            for obligation in obligation_result.scalars().all()
            if obligation.review_status != "rejected" and obligation.is_stale != "true"
        ]

        as_of = today or date.today()
        window_end = as_of + timedelta(days=days_ahead)
        deadlines: dict[tuple[date, str], DeadlineResponse] = {}
        undated_obligations = [
            UndatedObligationResponse(
                id=obligation.id,
                description=obligation.description,
                timing_description=obligation.deadline_description,
                timing_kind=DeadlineService._undated_timing_kind(
                    " ".join(
                        part
                        for part in (
                            obligation.description,
                            obligation.deadline_description,
                            obligation.source_quote,
                        )
                        if part
                    )
                ),
                source_section=obligation.source_section,
                source_quote=obligation.source_quote,
                certainty=obligation.certainty or "medium",
                review_status=obligation.review_status or "pending",
            )
            for obligation in obligations
            if obligation.deadline is None
        ]

        expiry_items = [
            item for item in items if item.item_type == ItemType.EXPIRY.value
        ]
        dated_expiries = [
            (item, DeadlineService._expiry_date(item))
            for item in expiry_items
        ]
        distinct_expiry_dates = {
            expiry_date for _, expiry_date in dated_expiries if expiry_date is not None
        }
        expiry_conflict = len(distinct_expiry_dates) > 1
        for expiry, expiry_date in dated_expiries:
            if expiry_date is None:
                logger.warning(
                    "Could not parse expiry date for extracted item %s (version %s)",
                    expiry.id,
                    contract_version_id,
                )
                continue
            if as_of <= expiry_date <= window_end:
                deadlines[(expiry_date, "expiry")] = DeadlineResponse(
                    id=expiry.id,
                    description=(
                        f"Uncertain expiry: {expiry.description or 'Contract expiry'}"
                        if expiry_conflict
                        else expiry.description or "Contract expiry"
                    ),
                    deadline=expiry_date,
                    days_remaining=(expiry_date - as_of).days,
                    type="expiry",
                    source_section=expiry.source_section,
                    certainty="low" if expiry_conflict else expiry.certainty or "medium",
                    review_status=expiry.review_status or "pending",
                )

        renewal_rules = [
            item
            for item in items
            if item.notice_period_days
            and (
                item.item_type == ItemType.RENEWAL.value
                or (
                    item.item_type == ItemType.NOTICE.value
                    and DeadlineService._is_renewal_notice(item)
                )
            )
        ]

        for expiry, expiry_date in dated_expiries:
            if expiry_date is None:
                continue
            for rule in renewal_rules:
                renewal_date = DateCalculator.calculate_renewal_deadline(
                    expiry_date, rule.notice_period_days
                )
                key = (renewal_date, "renewal")
                if as_of <= renewal_date <= window_end and key not in deadlines:
                    renewal_kind = DeadlineService._renewal_deadline_kind(rule)
                    deadlines[key] = DeadlineResponse(
                        id=rule.id,
                        description=(
                            (
                                f"Uncertain {renewal_kind} deadline assuming expiry "
                                f"{expiry_date.isoformat()} "
                                f"({rule.notice_period_days} days before expiry)"
                            )
                            if expiry_conflict
                            else (
                                f"{renewal_kind.capitalize()} deadline "
                                f"({rule.notice_period_days} days before expiry)"
                            )
                        ),
                        deadline=renewal_date,
                        days_remaining=(renewal_date - as_of).days,
                        type="renewal",
                        source_section=rule.source_section,
                        certainty="low" if expiry_conflict else rule.certainty or "medium",
                        review_status=rule.review_status or "pending",
                    )

        for obligation in obligations:
            if obligation.deadline is None:
                continue
            obligation_date = (
                obligation.deadline.date()
                if isinstance(obligation.deadline, datetime)
                else obligation.deadline
            )
            if as_of <= obligation_date <= window_end:
                deadlines[(obligation_date, "obligation")] = DeadlineResponse(
                    id=obligation.id,
                    description=obligation.description,
                    deadline=obligation_date,
                    days_remaining=(obligation_date - as_of).days,
                    type="obligation",
                    source_section=obligation.source_section,
                    certainty=obligation.certainty or "medium",
                    review_status=obligation.review_status or "pending",
                )

        ordered = sorted(deadlines.values(), key=lambda item: item.deadline)
        logger.info(
            "Calculated %s upcoming deadlines for contract_version_id=%s",
            len(ordered),
            contract_version_id,
        )
        return UpcomingDeadlinesResponse(
            deadlines=ordered,
            total=len(ordered),
            undated_obligations=undated_obligations,
        )

    @staticmethod
    def _undated_timing_kind(description: str | None) -> str:
        if not description:
            return "unspecified"
        if re.search(
            r"\b(?:each|every|monthly|weekly|daily|annually|annual|quarterly|per month|per year)\b",
            description,
            flags=re.IGNORECASE,
        ):
            return "recurring"
        return "trigger_dependent"

    @staticmethod
    def _expiry_date(item: ExtractedItem) -> date | None:
        if item.date_value is not None:
            if isinstance(item.date_value, datetime):
                return item.date_value.date()
            return item.date_value

        for text in (item.value, item.description, item.source_quote):
            parsed = DateCalculator.parse_date_string(text)
            if parsed is not None:
                return parsed
        return None

    @staticmethod
    def _is_renewal_notice(item: ExtractedItem) -> bool:
        text = " ".join(
            part
            for part in (item.purpose, item.description, item.source_quote)
            if part
        ).casefold()
        return bool(
            re.search(r"renew(?:al|al discussion|al notice|al period)?|non[\W_]*renew", text)
        )

    @staticmethod
    def _renewal_deadline_kind(item: ExtractedItem) -> str:
        text = " ".join(
            part
            for part in (
                item.purpose,
                item.description,
                item.source_quote,
            )
            if part
        ).casefold()
        if re.search(r"\bdiscussions?\b", text):
            return "renewal discussion"
        if re.search(r"\bnotices?\b|non[\W_]*renew", text):
            return "renewal notice"
        return "renewal"
