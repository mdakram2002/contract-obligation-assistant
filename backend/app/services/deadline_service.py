from datetime import date, datetime, timedelta
import logging
import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract_version import ContractVersion
from app.models.extracted_item import ExtractedItem, ItemType
from app.models.obligation import Obligation
from app.schemas.deadlines import DeadlineResponse, UpcomingDeadlinesResponse
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

        expiry_items = [
            item for item in items if item.item_type == ItemType.EXPIRY.value
        ]
        for expiry in expiry_items:
            expiry_date = DeadlineService._expiry_date(expiry)
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
                    description=expiry.description or "Contract expiry",
                    deadline=expiry_date,
                    days_remaining=(expiry_date - as_of).days,
                    type="expiry",
                    source_section=expiry.source_section,
                    certainty=expiry.certainty or "medium",
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

        for expiry in expiry_items:
            expiry_date = DeadlineService._expiry_date(expiry)
            if expiry_date is None:
                continue
            for rule in renewal_rules:
                renewal_date = DateCalculator.calculate_renewal_deadline(
                    expiry_date, rule.notice_period_days
                )
                key = (renewal_date, "renewal")
                if as_of <= renewal_date <= window_end and key not in deadlines:
                    deadlines[key] = DeadlineResponse(
                        id=rule.id,
                        description=(
                            f"Renewal discussion / notice "
                            f"({rule.notice_period_days} days before expiry)"
                        ),
                        deadline=renewal_date,
                        days_remaining=(renewal_date - as_of).days,
                        type="renewal",
                        source_section=rule.source_section,
                        certainty=rule.certainty or "medium",
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
                )

        ordered = sorted(deadlines.values(), key=lambda item: item.deadline)
        logger.info(
            "Calculated %s upcoming deadlines for contract_version_id=%s",
            len(ordered),
            contract_version_id,
        )
        return UpcomingDeadlinesResponse(deadlines=ordered, total=len(ordered))

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
