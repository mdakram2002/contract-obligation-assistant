from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID


class ContractCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class ContractResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ContractListResponse(BaseModel):
    contracts: list[ContractResponse]
    total: int
