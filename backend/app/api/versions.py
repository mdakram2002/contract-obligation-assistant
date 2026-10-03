from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.version import VersionListResponse, StaleDetectionResponse
from app.services.version_service import VersionService
from app.services.stale_detection import StaleDetectionService
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/versions", tags=["versions"])


@router.get("/contract/{contract_id}", response_model=VersionListResponse)
async def get_contract_versions(
    contract_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all versions of a contract.
    """
    try:
        contract_uuid = uuid.UUID(contract_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid contract_id format")

    versions = await VersionService.get_contract_versions(contract_uuid, db)

    return VersionListResponse(
        versions=versions,
        total=len(versions)
    )


@router.post("/detect-stale/{version_id}", response_model=StaleDetectionResponse)
async def detect_stale_items(
    version_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Detect stale items by comparing this version with the previous version.
    Marks previous version items as stale if they differ from new version.
    """
    try:
        version_uuid = uuid.UUID(version_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid version_id format")

    try:
        result = await StaleDetectionService.detect_stale_items(version_uuid, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Stale detection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Stale detection failed: {str(e)}")
