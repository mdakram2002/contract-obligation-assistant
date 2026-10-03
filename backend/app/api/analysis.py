from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.analysis import AnalysisRequest, AnalysisResponse
from app.services.analysis_service import AnalysisService
from app.services.summary_service import SummaryService
from app.models.party import Party
from app.models.extracted_item import ExtractedItem
from app.models.obligation import Obligation
from app.models.ambiguity import Ambiguity
from app.models.clarification_question import ClarificationQuestion
from app.models.application_log import EventType, LogLevel
from app.logging.service import LoggingService
from sqlalchemy import select
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_contract(
    request: AnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze a contract version using AI.
    Returns extracted information including parties, obligations, and ambiguities.
    """
    try:
        contract_version_id = uuid.UUID(request.contract_version_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid contract_version_id format")

    # Run analysis
    analysis_service = AnalysisService()
    try:
        result = await analysis_service.analyze_contract_version(contract_version_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    # Fetch all extracted data
    parties_result = await db.execute(
        select(Party).where(Party.contract_version_id == contract_version_id)
    )
    parties = parties_result.scalars().all()

    extracted_items_result = await db.execute(
        select(ExtractedItem).where(ExtractedItem.contract_version_id == contract_version_id)
    )
    extracted_items = extracted_items_result.scalars().all()

    obligations_result = await db.execute(
        select(Obligation).where(Obligation.contract_version_id == contract_version_id)
    )
    obligations = obligations_result.scalars().all()

    ambiguities_result = await db.execute(
        select(Ambiguity).where(Ambiguity.contract_version_id == contract_version_id)
    )
    ambiguities = ambiguities_result.scalars().all()

    questions_result = await db.execute(
        select(ClarificationQuestion).where(ClarificationQuestion.contract_version_id == contract_version_id)
    )
    questions = questions_result.scalars().all()

    # Log event
    await LoggingService.log_event(
        db,
        event_type=EventType.AI_ANALYSIS_COMPLETED,
        contract_version_id=str(contract_version_id),
        message=f"AI analysis completed: {len(parties)} parties, {len(extracted_items)} items, {len(obligations)} obligations",
        metadata={
            "ai_run_id": str(result["ai_run_id"]),
            "duration_ms": result["duration_ms"],
            "parties_count": len(parties),
            "items_count": len(extracted_items),
            "obligations_count": len(obligations)
        }
    )

    return AnalysisResponse(
        contract_version_id=contract_version_id,
        parties=parties,
        extracted_items=extracted_items,
        obligations=obligations,
        ambiguities=ambiguities,
        clarification_questions=questions,
        ai_run_id=result["ai_run_id"],
        analysis_status=result["status"]
    )


@router.post("/summary")
async def generate_summary(
    contract_version_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a reviewed contract summary.
    Only includes approved items (or user-edited items).
    """
    try:
        summary = await SummaryService.generate_summary(contract_version_id, db)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Summary generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")
