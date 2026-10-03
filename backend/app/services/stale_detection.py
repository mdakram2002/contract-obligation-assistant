from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.contract_version import ContractVersion
from app.models.extracted_item import ExtractedItem, ItemType
from app.models.obligation import Obligation
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class StaleDetectionService:
    """Detect and mark stale items when new contract versions are created."""

    @staticmethod
    async def detect_stale_items(
        new_version_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Compare new version with previous version and mark potentially stale items.
        Returns summary of changes detected.
        """
        # Get new version
        result = await db.execute(
            select(ContractVersion).where(ContractVersion.id == new_version_id)
        )
        new_version = result.scalar_one_or_none()
        if not new_version:
            raise ValueError("New version not found")

        # Get previous version
        prev_result = await db.execute(
            select(ContractVersion)
            .where(
                ContractVersion.contract_id == new_version.contract_id,
                ContractVersion.version_number == new_version.version_number - 1
            )
        )
        prev_version = prev_result.scalar_one_or_none()

        if not prev_version:
            logger.info(f"No previous version found for contract_id={new_version.contract_id}")
            return {"stale_count": 0, "changed_fields": []}

        # Get extracted items from both versions
        new_items_result = await db.execute(
            select(ExtractedItem).where(ExtractedItem.contract_version_id == new_version.id)
        )
        new_items = new_items_result.scalars().all()

        prev_items_result = await db.execute(
            select(ExtractedItem).where(ExtractedItem.contract_version_id == prev_version.id)
        )
        prev_items = prev_items_result.scalars().all()

        # Get obligations from both versions
        new_obligations_result = await db.execute(
            select(Obligation).where(Obligation.contract_version_id == new_version.id)
        )
        new_obligations = new_obligations_result.scalars().all()

        prev_obligations_result = await db.execute(
            select(Obligation).where(Obligation.contract_version_id == prev_version.id)
        )
        prev_obligations = prev_obligations_result.scalars().all()

        # Compare and detect changes
        stale_count = 0
        changed_fields = []

        # Compare extracted items by type and title
        prev_items_dict = {(item.item_type, item.title): item for item in prev_items}
        new_items_dict = {(item.item_type, item.title): item for item in new_items}

        for key, prev_item in prev_items_dict.items():
            if key in new_items_dict:
                new_item = new_items_dict[key]
                # Check for significant changes
                if StaleDetectionService._items_differ(prev_item, new_item):
                    # Mark previous item as stale
                    prev_item.is_stale = "true"
                    stale_count += 1
                    changed_fields.append({
                        "type": "extracted_item",
                        "item_type": prev_item.item_type,
                        "title": prev_item.title,
                        "change": "value_changed"
                    })
            else:
                # Item removed in new version
                prev_item.is_stale = "true"
                stale_count += 1
                changed_fields.append({
                    "type": "extracted_item",
                    "item_type": prev_item.item_type,
                    "title": prev_item.title,
                    "change": "removed"
                })

        # Compare obligations by description
        prev_obligations_dict = {oblig.description: obligation for obligation in prev_obligations}
        new_obligations_dict = {oblig.description: obligation for obligation in new_obligations}

        for key, prev_oblig in prev_obligations_dict.items():
            if key in new_obligations_dict:
                new_oblig = new_obligations_dict[key]
                # Check for significant changes
                if StaleDetectionService._obligations_differ(prev_oblig, new_oblig):
                    # Mark previous obligation as stale
                    prev_oblig.is_stale = "true"
                    stale_count += 1
                    changed_fields.append({
                        "type": "obligation",
                        "description": prev_oblig.description,
                        "change": "value_changed"
                    })
            else:
                # Obligation removed in new version
                prev_oblig.is_stale = "true"
                stale_count += 1
                changed_fields.append({
                    "type": "obligation",
                    "description": prev_oblig.description,
                    "change": "removed"
                })

        await db.commit()

        logger.info(
            f"Stale detection completed: {stale_count} items marked as stale "
            f"for contract_id={new_version.contract_id}"
        )

        return {
            "stale_count": stale_count,
            "changed_fields": changed_fields,
            "previous_version": prev_version.version_number,
            "new_version": new_version.version_number
        }

    @staticmethod
    def _items_differ(prev_item: ExtractedItem, new_item: ExtractedItem) -> bool:
        """Check if two extracted items have significantly different values."""
        # Check important fields
        if prev_item.value != new_item.value:
            return True
        if prev_item.notice_period_days != new_item.notice_period_days:
            return True
        if prev_item.description != new_item.description:
            return True
        if prev_item.date_value != new_item.date_value:
            return True
        return False

    @staticmethod
    def _obligations_differ(prev_oblig: Obligation, new_oblig: Obligation) -> bool:
        """Check if two obligations have significantly different values."""
        # Check important fields
        if prev_oblig.responsible_party != new_oblig.responsible_party:
            return True
        if prev_oblig.deadline != new_oblig.deadline:
            return True
        if prev_oblig.deadline_description != new_oblig.deadline_description:
            return True
        return False
