# ─────────────────────────────────────────────────────────────────────────────
# NEW FILE — app/schemas/admin/document_field_config.py
# ─────────────────────────────────────────────────────────────────────────────

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DocumentFieldConfigCreateRequest(BaseModel):
    ocr_slug: str
    field_name: str
    is_mandatory: bool = True
    is_expiry_field: bool = False
    display_order: int = 0


class DocumentFieldConfigUpdateRequest(BaseModel):
    is_mandatory: Optional[bool] = None
    is_expiry_field: Optional[bool] = None
    display_order: Optional[int] = None


class DocumentFieldConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ocr_slug: str
    field_name: str
    is_mandatory: bool
    is_expiry_field: bool
    display_order: int
    created_at: datetime
    updated_at: Optional[datetime] = None