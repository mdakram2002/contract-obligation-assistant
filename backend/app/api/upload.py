from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import uuid
from app.database import get_db
from app.schemas.document import DocumentUploadResponse, PastedTextRequest, PastedTextResponse
from app.schemas.contract import ContractCreate, ContractResponse
from app.services.document_parser import DocumentParser
from app.services.stale_detection import StaleDetectionService
from app.models.contract import Contract, ContractStatus
from app.models.contract_version import ContractVersion
from app.models.application_log import EventType, LogLevel
from app.logging.service import LoggingService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    contract_id: Optional[str] = None,
    contract_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a contract document (PDF or DOCX).
    If contract_id is provided, creates a new version of existing contract.
    If contract_name is provided (and no contract_id), creates a new contract.
    If neither is provided, creates a new contract with auto-generated name.
    """
    # Validate file size
    MAX_SIZE = 10 * 1024 * 1024  # 10MB
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB.")

    # Validate file type
    try:
        file_type = DocumentParser.validate_file_type(file.filename, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Parse document
    try:
        text, metadata = DocumentParser.parse_document(content, file_type)
    except Exception as e:
        logger.error(f"Document parsing failed: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Failed to parse document: {str(e)}")

    # Handle contract creation or versioning
    if contract_id:
        # Create new version of existing contract
        result = await db.execute(select(Contract).where(Contract.id == uuid.UUID(contract_id)))
        contract = result.scalar_one_or_none()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")

        # Get next version number
        version_result = await db.execute(
            select(ContractVersion)
            .where(ContractVersion.contract_id == contract.id)
            .order_by(ContractVersion.version_number.desc())
        )
        last_version = version_result.scalar_one_or_none()
        next_version = (last_version.version_number + 1) if last_version else 1

    else:
        # Create new contract
        contract = Contract(
            name=contract_name or f"Contract {file.filename}",
            status="draft"
        )
        db.add(contract)
        await db.flush()
        next_version = 1

    # Create contract version
    contract_version = ContractVersion(
        contract_id=contract.id,
        version_number=next_version,
        file_name=file.filename,
        file_type=file_type,
        raw_text=text,
        parsing_metadata=metadata
    )
    db.add(contract_version)
    await db.commit()
    await db.refresh(contract_version)

    # Detect stale items if this is not the first version
    if next_version > 1:
        try:
            await StaleDetectionService.detect_stale_items(contract_version.id, db)
        except Exception as e:
            logger.warning(f"Stale detection failed after upload: {str(e)}")

    logger.info(f"Document uploaded: contract_id={contract.id}, version_id={contract_version.id}")

    # Log event
    await LoggingService.log_event(
        db,
        event_type=EventType.DOCUMENT_UPLOADED,
        contract_id=str(contract.id),
        contract_version_id=str(contract_version.id),
        message=f"Document uploaded: {file.filename}",
        metadata={"file_type": file_type, "version_number": next_version}
    )

    return DocumentUploadResponse(
        contract_id=str(contract.id),
        version_id=str(contract_version.id),
        version_number=contract_version.version_number,
        file_name=contract_version.file_name,
        file_type=contract_version.file_type,
        text_length=len(text),
        metadata=metadata
    )


@router.post("/paste-text", response_model=PastedTextResponse)
async def paste_text(
    request: PastedTextRequest,
    contract_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit pasted contract text.
    If contract_id is provided, creates a new version of existing contract.
    If contract_name is provided (and no contract_id), creates a new contract.
    If neither is provided, creates a new contract with auto-generated name.
    """
    # Parse text
    try:
        text, metadata = DocumentParser.parse_text(request.text)
    except Exception as e:
        logger.error(f"Text parsing failed: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Failed to parse text: {str(e)}")

    # Handle contract creation or versioning
    contract_id = request.contract_id
    if contract_id:
        # Create new version of existing contract
        result = await db.execute(select(Contract).where(Contract.id == uuid.UUID(contract_id)))
        contract = result.scalar_one_or_none()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")

        # Get next version number
        version_result = await db.execute(
            select(ContractVersion)
            .where(ContractVersion.contract_id == contract.id)
            .order_by(ContractVersion.version_number.desc())
        )
        last_version = version_result.scalar_one_or_none()
        next_version = (last_version.version_number + 1) if last_version else 1

    else:
        # Create new contract
        contract = Contract(
            name=contract_name or "Pasted Contract",
            status="draft"
        )
        db.add(contract)
        await db.flush()
        next_version = 1

    # Create contract version
    contract_version = ContractVersion(
        contract_id=contract.id,
        version_number=next_version,
        file_name=None,
        file_type="text",
        raw_text=text,
        parsing_metadata=metadata
    )
    db.add(contract_version)
    await db.commit()
    await db.refresh(contract_version)

    # Detect stale items if this is not the first version
    if next_version > 1:
        try:
            await StaleDetectionService.detect_stale_items(contract_version.id, db)
        except Exception as e:
            logger.warning(f"Stale detection failed after paste: {str(e)}")

    logger.info(f"Text pasted: contract_id={contract.id}, version_id={contract_version.id}")

    # Log event
    await LoggingService.log_event(
        db,
        event_type=EventType.DOCUMENT_UPLOADED,
        contract_id=str(contract.id),
        contract_version_id=str(contract_version.id),
        message="Pasted text uploaded",
        metadata={"file_type": "text", "version_number": next_version}
    )

    return PastedTextResponse(
        contract_id=str(contract.id),
        version_id=str(contract_version.id),
        version_number=contract_version.version_number,
        text_length=len(text),
        metadata=metadata
    )
