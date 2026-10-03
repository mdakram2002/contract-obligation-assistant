from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


class ApproveRequest(BaseModel):
    item_id: str
    item_type: str  # "extracted_item" or "obligation"
    notes: Optional[str] = None


class RejectRequest(BaseModel):
    item_id: str
    item_type: str  # "extracted_item" or "obligation"
    notes: Optional[str] = None


class EditRequest(BaseModel):
    item_id: str
    item_type: str  # "extracted_item" or "obligation"
    updates: dict  # Flexible field updates
    notes: Optional[str] = None


class ReviewActionResponse(BaseModel):
    id: UUID
    action_type: str
    extracted_item_id: Optional[UUID] = None
    obligation_id: Optional[UUID] = None
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    notes: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class ItemStatusResponse(BaseModel):
    id: UUID
    review_status: str
    user_edited: str
    updated_at: str

    class Config:
        from_attributes = True
