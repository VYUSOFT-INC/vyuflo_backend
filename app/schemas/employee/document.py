import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from enum import Enum

class DocumentStatus(str, Enum):
    required            = "required"
    uploaded            = "uploaded"
    pending_review      = "pending_review"
    verified            = "verified"
    rejected            = "rejected"
    missing             = "missing"
    pending_hr_release  = "pending_hr_release"
    expired             = "expired"
    superseded          = "superseded"

class DocumentResponse(BaseModel):
    id:              uuid.UUID
    user_id:         uuid.UUID
    application_id:  Optional[uuid.UUID]
    document_type_id: uuid.UUID
    name:            str
    file_size_bytes: int
    file_type:       str
    status:          DocumentStatus
    document_type:   Optional[str]
    category:        Optional[str]
    uploaded_at:     datetime
    verified_at:     Optional[datetime]
    rejection_reason: Optional[str]
    total_pages:     Optional[int]
    ocr_status:      str
    version:         int
    in_use: bool = False
    activates_on: Optional[date] = None
    task_id:         Optional[uuid.UUID] = None
    task_name:       Optional[str]       = None
    assigned_to_attorney_at: Optional[datetime] = None   # ADD
    assigned_to_attorney_by: Optional[uuid.UUID] = None  # ADD

    model_config = ConfigDict(from_attributes=True)

class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int

class RenameDocumentRequest(BaseModel):
    new_name: str