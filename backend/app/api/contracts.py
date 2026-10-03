from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.schemas.contract import ContractResponse, ContractListResponse
from app.models.contract import Contract
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contracts", tags=["contracts"])


@router.get("", response_model=ContractListResponse)
async def list_contracts(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    List all contracts with pagination.
    """
    result = await db.execute(
        select(Contract)
        .order_by(Contract.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    contracts = result.scalars().all()

    # Get total count
    count_result = await db.execute(select(Contract))
    total = len(count_result.scalars().all())

    return ContractListResponse(
        contracts=contracts,
        total=total
    )


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific contract by ID.
    """
    import uuid
    try:
        contract_uuid = uuid.UUID(contract_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid contract_id format")

    result = await db.execute(
        select(Contract).where(Contract.id == contract_uuid)
    )
    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    return contract
