import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from enum import Enum

class DocumentStatus(str, Enum):
    required       = "required"
    uploaded       = "uploaded"
    pending_review = "pending_review"
    verified       = "verified"
    rejected       = "rejected"
    missing        = "missing"
    expired        = "expired"
    superseded     = "superseded"

class DocumentResponse(BaseModel):
    id:              uuid.UUID
    user_id:         uuid.UUID
    application_id:  Optional[uuid.UUID]
    document_type_id: uuid.UUID
    # ← frontend-friendly field names
    name:            str              # = file_name
    file_size_bytes: int              # = file_size_kb * 1024
    file_type:       str              # = file_format
    status:          DocumentStatus
    document_type:   Optional[str]    # from DocumentType.name
    category:        Optional[str]    # from DocumentType.category
    uploaded_at:     datetime         # = created_at
    verified_at:     Optional[datetime]
    rejection_reason: Optional[str]
    total_pages:     Optional[int]
    ocr_status:      str
    version:         int
    in_use: bool = False
    activates_on: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)

class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int

class RenameDocumentRequest(BaseModel):
    new_name: str