from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.deadlines import (
    DeadlineCalculationRequest,
    UpcomingDeadlinesResponse,
)
from app.services.deadline_service import DeadlineService
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/deadlines", tags=["deadlines"])


@router.post("/calculate", response_model=UpcomingDeadlinesResponse)
async def calculate_deadlines(
    request: DeadlineCalculationRequest,
    days_ahead: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Calculate upcoming dates for the selected contract version."""
    try:
        contract_version_id = uuid.UUID(request.contract_version_id)
        contract_id = uuid.UUID(request.contract_id) if request.contract_id else None
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid contract_id or contract_version_id format",
        )

    try:
        return await DeadlineService.calculate_for_version(
            contract_version_id=contract_version_id,
            contract_id=contract_id,
            days_ahead=days_ahead,
            db=db,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
