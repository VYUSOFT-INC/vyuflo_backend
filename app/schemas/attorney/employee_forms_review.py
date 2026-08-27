"""
employee_forms_review.py — Pydantic schemas for attorney review actions
on employee-filled forms (I-9, I-983, ...).
"""

from pydantic import BaseModel, Field
from typing import Literal


class RequestCorrectionsPayload(BaseModel):
    target: Literal["employee", "hr"] = Field(..., description="Who needs to fix this")  
    fields: list[str] = Field(default_factory=list, description="e.g. ['ssn', 'zip_code']")  
    review_note: str = Field(..., min_length=1, description="What needs to be fixed")


class ApproveFormPayload(BaseModel):
    review_note: str | None = Field(None, description="Optional approval note")