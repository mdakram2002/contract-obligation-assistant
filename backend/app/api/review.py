from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.database import get_db
from app.schemas.review import ApproveRequest, RejectRequest, EditRequest, ReviewActionResponse, ItemStatusResponse
from app.models.extracted_item import ExtractedItem, ReviewStatus
from app.models.obligation import Obligation
from app.models.review_action import ReviewAction, ActionType
from app.models.application_log import EventType, LogLevel
from app.logging.service import LoggingService
from datetime import datetime
import uuid
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/review", tags=["review"])


@router.post("/approve", response_model=ItemStatusResponse)
async def approve_item(
    request: ApproveRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Approve an extracted item or obligation.
    Creates a review action record and updates the item status.
    """
    try:
        item_id = uuid.UUID(request.item_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid item_id format")

    # Determine item type and fetch
    if request.item_type == "extracted_item":
        result = await db.execute(
            select(ExtractedItem).where(ExtractedItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Extracted item not found")

        # Create review action
        action = ReviewAction(
            action_type=ActionType.APPROVED,
            extracted_item_id=item_id,
            notes=request.notes
        )
        db.add(action)

        # Update item status
        item.review_status = ReviewStatus.APPROVED
        item.updated_at = datetime.utcnow()

    elif request.item_type == "obligation":
        result = await db.execute(
            select(Obligation).where(Obligation.id == item_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Obligation not found")

        # Create review action
        action = ReviewAction(
            action_type=ActionType.APPROVED,
            obligation_id=item_id,
            notes=request.notes
        )
        db.add(action)

        # Update item status
        item.review_status = ReviewStatus.APPROVED
        item.updated_at = datetime.utcnow()

    else:
        raise HTTPException(status_code=400, detail="Invalid item_type")

    await db.commit()
    await db.refresh(item)

    logger.info(f"Item approved: item_id={item_id}, item_type={request.item_type}")

    # Log event
    await LoggingService.log_event(
        db,
        event_type=EventType.ITEM_APPROVED,
        contract_version_id=str(item.contract_version_id) if hasattr(item, 'contract_version_id') else None,
        message=f"Item approved: {request.item_type}",
        metadata={"item_id": str(item_id), "item_type": request.item_type, "notes": request.notes}
    )

    return ItemStatusResponse(
        id=item.id,
        review_status=item.review_status,
        user_edited=item.user_edited,
        updated_at=item.updated_at.isoformat()
    )


@router.post("/reject", response_model=ItemStatusResponse)
async def reject_item(
    request: RejectRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Reject an extracted item or obligation.
    Creates a review action record and updates the item status.
    """
    try:
        item_id = uuid.UUID(request.item_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid item_id format")

    # Determine item type and fetch
    if request.item_type == "extracted_item":
        result = await db.execute(
            select(ExtractedItem).where(ExtractedItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Extracted item not found")

        # Create review action
        action = ReviewAction(
            action_type=ActionType.REJECTED,
            extracted_item_id=item_id,
            notes=request.notes
        )
        db.add(action)

        # Update item status
        item.review_status = ReviewStatus.REJECTED
        item.updated_at = datetime.utcnow()

    elif request.item_type == "obligation":
        result = await db.execute(
            select(Obligation).where(Obligation.id == item_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Obligation not found")

        # Create review action
        action = ReviewAction(
            action_type=ActionType.REJECTED,
            obligation_id=item_id,
            notes=request.notes
        )
        db.add(action)

        # Update item status
        item.review_status = ReviewStatus.REJECTED
        item.updated_at = datetime.utcnow()

    else:
        raise HTTPException(status_code=400, detail="Invalid item_type")

    await db.commit()
    await db.refresh(item)

    logger.info(f"Item rejected: item_id={item_id}, item_type={request.item_type}")

    # Log event
    await LoggingService.log_event(
        db,
        event_type=EventType.ITEM_REJECTED,
        contract_version_id=str(item.contract_version_id) if hasattr(item, 'contract_version_id') else None,
        message=f"Item rejected: {request.item_type}",
        metadata={"item_id": str(item_id), "item_type": request.item_type, "notes": request.notes}
    )

    return ItemStatusResponse(
        id=item.id,
        review_status=item.review_status,
        user_edited=item.user_edited,
        updated_at=item.updated_at.isoformat()
    )


@router.post("/edit", response_model=ItemStatusResponse)
async def edit_item(
    request: EditRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Edit an extracted item or obligation.
    Creates a review action record with previous and new values.
    """
    try:
        item_id = uuid.UUID(request.item_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid item_id format")

    # Determine item type and fetch
    if request.item_type == "extracted_item":
        result = await db.execute(
            select(ExtractedItem).where(ExtractedItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Extracted item not found")

        # Store previous values as JSON
        previous_values = {}
        for field, value in request.updates.items():
            if hasattr(item, field):
                previous_values[field] = str(getattr(item, field))

        # Update item fields
        for field, value in request.updates.items():
            if hasattr(item, field):
                setattr(item, field, value)

        # Create review action
        action = ReviewAction(
            action_type=ActionType.EDITED,
            extracted_item_id=item_id,
            previous_value=json.dumps(previous_values),
            new_value=json.dumps(request.updates),
            notes=request.notes
        )
        db.add(action)

        # Mark as user edited
        item.user_edited = "true"
        item.updated_at = datetime.utcnow()

    elif request.item_type == "obligation":
        result = await db.execute(
            select(Obligation).where(Obligation.id == item_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Obligation not found")

        # Store previous values as JSON
        previous_values = {}
        for field, value in request.updates.items():
            if hasattr(item, field):
                previous_values[field] = str(getattr(item, field))

        # Update item fields
        for field, value in request.updates.items():
            if hasattr(item, field):
                setattr(item, field, value)

        # Create review action
        action = ReviewAction(
            action_type=ActionType.EDITED,
            obligation_id=item_id,
            previous_value=json.dumps(previous_values),
            new_value=json.dumps(request.updates),
            notes=request.notes
        )
        db.add(action)

        # Mark as user edited
        item.user_edited = "true"
        item.updated_at = datetime.utcnow()

    else:
        raise HTTPException(status_code=400, detail="Invalid item_type")

    await db.commit()
    await db.refresh(item)

    logger.info(f"Item edited: item_id={item_id}, item_type={request.item_type}")

    # Log event
    await LoggingService.log_event(
        db,
        event_type=EventType.ITEM_EDITED,
        contract_version_id=str(item.contract_version_id) if hasattr(item, 'contract_version_id') else None,
        message=f"Item edited: {request.item_type}",
        metadata={"item_id": str(item_id), "item_type": request.item_type, "notes": request.notes}
    )

    return ItemStatusResponse(
        id=item.id,
        review_status=item.review_status,
        user_edited=item.user_edited,
        updated_at=item.updated_at.isoformat()
    )
