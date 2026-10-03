from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.contract import Contract
from app.models.contract_version import ContractVersion
from typing import List
import logging

logger = logging.getLogger(__name__)


class VersionService:
    """Service for contract version management."""

    @staticmethod
    async def get_contract_versions(
        contract_id: str,
        db: AsyncSession
    ) -> List[ContractVersion]:
        """
        Get all versions of a contract.
        """
        result = await db.execute(
            select(ContractVersion)
            .where(ContractVersion.contract_id == contract_id)
            .order_by(ContractVersion.version_number.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_contract_by_version(
        version_id: str,
        db: AsyncSession
    ) -> Contract:
        """
        Get the contract for a specific version.
        """
        result = await db.execute(
            select(ContractVersion).where(ContractVersion.id == version_id)
        )
        version = result.scalar_one_or_none()
        if not version:
            raise ValueError("Version not found")

        result = await db.execute(
            select(Contract).where(Contract.id == version.contract_id)
        )
        return result.scalar_one()
