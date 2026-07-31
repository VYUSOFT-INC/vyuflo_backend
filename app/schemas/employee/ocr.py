# app/schemas/ocr.py
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class OCRFieldResponse(BaseModel):
    id:               Optional[uuid.UUID] = None
    document_id:      uuid.UUID
    field_name:       str
    extracted_value:  Optional[str]
    confidence_score: Optional[int]
    needs_review:     bool
    is_confirmed:     bool
    confirmed_at:     Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class OCRFieldCreate(BaseModel):
    """Used internally — no id, pure insert."""
    field_name:       str
    extracted_value:  str
    confidence_score: int
    needs_review:     bool


class OCRFieldUpsertItem(BaseModel):
    """Used by the save endpoint — id present on update, absent on first insert."""
    id:               Optional[uuid.UUID] = None   # ← real DB UUID on re-open, None on first save
    field_name:       str
    extracted_value:  str
    confidence_score: int
    needs_review:     bool


class SaveOCRFieldsRequest(BaseModel):
    fields: list[OCRFieldUpsertItem]          # ← was OCRFieldCreate, now accepts id


class OCRFieldUpdate(BaseModel):
    extracted_value:  Optional[str]  = None
    is_confirmed:     Optional[bool] = None