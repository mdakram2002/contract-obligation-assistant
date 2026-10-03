from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.contract import Contract
from app.models.contract_version import ContractVersion
from app.models.party import Party
from app.models.extracted_item import ExtractedItem, ReviewStatus
from app.models.obligation import Obligation
from app.models.ambiguity import Ambiguity
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class SummaryService:
    """Service for generating reviewed contract summaries."""

    @staticmethod
    async def generate_summary(
        contract_version_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Generate a summary of reviewed contract information.
        Only includes approved items (or user-edited items).
        """
        try:
            version_uuid = contract_version_id  # Assuming it's already a UUID string
        except ValueError:
            raise ValueError("Invalid contract_version_id format")

        # Fetch contract version
        version_result = await db.execute(
            select(ContractVersion).where(ContractVersion.id == version_uuid)
        )
        version = version_result.scalar_one_or_none()
        if not version:
            raise ValueError("Contract version not found")

        # Fetch contract
        contract_result = await db.execute(
            select(Contract).where(Contract.id == version.contract_id)
        )
        contract = contract_result.scalar_one_or_none()

        # Fetch parties
        parties_result = await db.execute(
            select(Party).where(Party.contract_version_id == version_uuid)
        )
        parties = parties_result.scalars().all()

        # Fetch approved extracted items (or user-edited)
        approved_items_result = await db.execute(
            select(ExtractedItem).where(
                ExtractedItem.contract_version_id == version_uuid,
                ExtractedItem.review_status.in_([ReviewStatus.APPROVED])
            )
        )
        approved_items = approved_items_result.scalars().all()

        # Fetch approved obligations (or user-edited)
        approved_obligations_result = await db.execute(
            select(Obligation).where(
                Obligation.contract_version_id == version_uuid,
                Obligation.review_status.in_([ReviewStatus.APPROVED])
            )
        )
        approved_obligations = approved_obligations_result.scalars().all()

        # Fetch unresolved ambiguities
        ambiguities_result = await db.execute(
            select(Ambiguity).where(Ambiguity.contract_version_id == version_uuid)
        )
        ambiguities = ambiguities_result.scalars().all()

        # Group extracted items by type
        items_by_type = {}
        for item in approved_items:
            if item.item_type not in items_by_type:
                items_by_type[item.item_type] = []
            items_by_type[item.item_type].append({
                "title": item.title,
                "value": item.value,
                "source_section": item.source_section,
                "source_page": item.source_page,
                "certainty": item.certainty.value if item.certainty else None
            })

        # Format obligations
        obligations_summary = []
        for obl in approved_obligations:
            obligations_summary.append({
                "description": obl.description,
                "deadline": obl.deadline.isoformat() if obl.deadline else None,
                "responsible_party": obl.responsible_party,
                "source_section": obl.source_section,
                "source_page": obl.source_page,
                "certainty": obl.certainty.value if obl.certainty else None
            })

        # Format parties
        parties_summary = []
        for party in parties:
            parties_summary.append({
                "name": party.name,
                "role": party.role,
                "source_section": party.source_section,
                "source_page": party.source_page
            })

        # Format ambiguities
        ambiguities_summary = []
        for amb in ambiguities:
            ambiguities_summary.append({
                "description": amb.description,
                "affected_items": amb.affected_items,
                "suggested_action": amb.suggested_action
            })

        summary = {
            "contract_name": contract.name if contract else "Unknown",
            "version_number": version.version_number,
            "file_name": version.file_name,
            "parties": parties_summary,
            "extracted_items": items_by_type,
            "obligations": obligations_summary,
            "ambiguities": ambiguities_summary,
            "total_approved_items": len(approved_items),
            "total_approved_obligations": len(approved_obligations),
            "has_unresolved_ambiguities": len(ambiguities) > 0
        }

        logger.info(f"Summary generated for version {version_uuid}: {len(approved_items)} items, {len(approved_obligations)} obligations")

        return summary
