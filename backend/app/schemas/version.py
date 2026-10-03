from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID


class ContractVersionResponse(BaseModel):
    id: UUID
    contract_id: UUID
    version_number: int
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class VersionListResponse(BaseModel):
    versions: list[ContractVersionResponse]
    total: int


class StaleDetectionResponse(BaseModel):
    stale_count: int
    changed_fields: list[dict]
    previous_version: int
    new_version: int
