from pydantic import BaseModel, Field
from typing import Optional


class DocumentUploadResponse(BaseModel):
    contract_id: str
    version_id: str
    version_number: int
    file_name: str
    file_type: str
    text_length: int
    metadata: Optional[dict] = None


class PastedTextRequest(BaseModel):
    contract_id: Optional[str] = None
    text: str = Field(..., min_length=1)


class PastedTextResponse(BaseModel):
    contract_id: str
    version_id: str
    version_number: int
    text_length: int
    metadata: Optional[dict] = None
