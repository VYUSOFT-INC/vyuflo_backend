from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class VisaTypeResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: Optional[str] = None
    category: str
    requires_employer_sponsor: bool
    required_documents: Optional[str] = None
    typical_processing_days: Optional[int] = None
    government_fee_usd: Optional[int] = None
    uscis_url: Optional[str] = None
    short_label: Optional[str] = None
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VisaTypeListResponse(BaseModel):
    items: list[VisaTypeResponse]
    total: int