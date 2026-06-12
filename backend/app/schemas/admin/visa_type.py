"""
app/schemas/visa_type.py  ← COMPLETE FILE (with all fixes applied)

Covers every UI component on the Admin Visa Types Manager screen:
  - 4 KPI stat cards (total, active, pending_review, active_cases)
  - Visa type card listing (code, name, category, status, processing time,
    success_rate, required_docs count, active_cases count)
  - Search by name / code
  - Category filter dropdown
  - Status filter dropdown
  - Sort dropdown
  - Add New Visa Type modal (POST)
  - Edit inline (PATCH)
  - Status toggle (PATCH /toggle)
  - Export All (GET /export)
  - View Details (GET /{id})

FIXES APPLIED vs previous version:
  1. VisaTypeResponse.required_documents
       - Type changed from Optional[list[str]] → Optional[Any]
       - field_validator(mode="before") added to parse JSON string → list
         BEFORE Pydantic type-checks it (model_post_init was too late)
  2. VisaTypeResponse.success_rate
       - Was Optional[int] with NO default → Pydantic treated it as required
       - Fixed to Optional[int] = None  (column does not exist in DB yet)
  3. VisaTypeResponse.status
       - VisaType ORM model has NO status column (only is_active)
       - field_validator derives it from is_active if not explicitly set
  4. VisaTypeResponse.updated_at
       - Changed from required datetime → Optional[datetime] = None (safe)
  5. model_post_init kept but only for required_documents_count + status fallback
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ── allowed enum values (mirrored from visamodels.py) ────────────────────────
VALID_CATEGORIES = {
    "employment", "student", "visitor", "permanent_resident", "exchange"
}
VALID_STATUSES = {"active", "inactive", "pending_review"}


# =============================================================================
# SHARED BASE
# =============================================================================

class VisaTypeBase(BaseModel):
    code: str = Field(
        ..., max_length=50,
        description="Unique code: H-1B, F-1, O-1A"
    )
    name: str = Field(
        ..., max_length=200,
        description="Full name: H-1B Specialty Occupation"
    )
    short_label:               Optional[str] = Field(None, max_length=30)
    description:               Optional[str] = None
    category: str = Field(
        ...,
        description="employment|student|visitor|permanent_resident|exchange"
    )
    requires_employer_sponsor: bool          = False
    required_documents: Optional[str] = Field(
        None,
        description='JSON array stored as string: ["Passport Copy", "Offer Letter"]'
    )
    typical_processing_days: Optional[int] = Field(
        None, ge=1,
        description="Processing time in days"
    )
    government_fee_usd:  Optional[int] = Field(None, ge=0)
    uscis_url:           Optional[str] = Field(None, max_length=1000)
    display_order:       int           = 0
    is_active:           bool          = True

    # ── Fields needed for Admin UI ────────────────────────────────────────────
    status: Optional[str] = Field(
        "active",
        description="active | inactive | pending_review"
    )
    success_rate: Optional[int] = Field(
        None, ge=0, le=100,
        description="Admin-managed success rate %. Shown as '94%' on visa card."
    )

    @field_validator("category")
    @classmethod
    def check_category(cls, v: str) -> str:
        if v not in VALID_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_CATEGORIES}")
        return v

    @field_validator("status")
    @classmethod
    def check_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}")
        return v

    @field_validator("required_documents")
    @classmethod
    def validate_required_documents(cls, v: Optional[str]) -> Optional[str]:
        """Ensures the stored JSON string is actually a valid list."""
        if v is None:
            return v
        if isinstance(v, list):
            # accept list input → serialise to JSON string for storage
            return json.dumps(v)
        try:
            parsed = json.loads(v)
            if not isinstance(parsed, list):
                raise ValueError("required_documents must be a JSON array")
        except json.JSONDecodeError:
            raise ValueError("required_documents must be valid JSON")
        return v


# =============================================================================
# CREATE  (POST /admin/visa-types)
# Triggered by "Add New Visa Type" button
# =============================================================================

class VisaTypeCreate(VisaTypeBase):
    """All fields from the Add New Visa Type modal."""
    pass


# =============================================================================
# UPDATE  (PATCH /admin/visa-types/{id})
# Triggered by the "Edit" action on each card — all fields optional
# =============================================================================

class VisaTypeUpdate(BaseModel):
    name:                      Optional[str] = Field(None, max_length=200)
    short_label:               Optional[str] = Field(None, max_length=30)
    description:               Optional[str] = None
    category:                  Optional[str] = None
    requires_employer_sponsor: Optional[bool] = None
    required_documents:        Optional[str] = None
    typical_processing_days:   Optional[int] = Field(None, ge=1)
    government_fee_usd:        Optional[int] = Field(None, ge=0)
    uscis_url:                 Optional[str] = None
    display_order:             Optional[int] = None
    is_active:                 Optional[bool] = None
    status:                    Optional[str] = None
    success_rate:              Optional[int] = Field(None, ge=0, le=100)

    @field_validator("category")
    @classmethod
    def check_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_CATEGORIES}")
        return v

    @field_validator("status")
    @classmethod
    def check_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}")
        return v


# =============================================================================
# STATUS TOGGLE  (PATCH /admin/visa-types/{id}/toggle)
# The Active/Inactive badge toggle on each visa card
# =============================================================================

class VisaTypeToggle(BaseModel):
    """
    Dedicated toggle — keeps the general PATCH endpoint clean.
    Sets both `status` and `is_active` consistently in one call.
    """
    is_active: bool = Field(..., description="true → active, false → inactive")


# =============================================================================
# RESPONSE — Single visa type card
# Powers every visa card on the listing page and the View Details panel
#
# FIX 1: required_documents  → Optional[Any] + field_validator(mode="before")
#         Parses JSON string from DB into list BEFORE Pydantic validates type.
# FIX 2: success_rate        → Optional[int] = None  (no DB column yet)
# FIX 3: status              → Optional[str] = None  derived from is_active
# FIX 4: updated_at          → Optional[datetime] = None  (safe default)
# =============================================================================

class VisaTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # ── Identity ──────────────────────────────────────────────────────────────
    id:                        uuid.UUID
    code:                      str
    name:                      str
    short_label:               Optional[str]  = None
    description:               Optional[str]  = None
    category:                  str

    # ── Status ────────────────────────────────────────────────────────────────
    is_active:                 bool           = True
    status:                    Optional[str]  = None  # FIX 3: derived below

    # ── Sponsor / Docs ────────────────────────────────────────────────────────
    requires_employer_sponsor: bool           = False
    required_documents:        Optional[Any]  = None  # FIX 1: Any → parsed by validator
    required_documents_count:  int            = 0     # computed in model_post_init

    # ── Processing / Fees ─────────────────────────────────────────────────────
    typical_processing_days:   Optional[int]  = None
    processing_time_label:     Optional[str]  = None  # e.g. "6-8 months" — set by service
    government_fee_usd:        Optional[int]  = None
    uscis_url:                 Optional[str]  = None

    # ── KPI figures on card ───────────────────────────────────────────────────
    success_rate:              Optional[int]  = None  # FIX 2: = None default added
    active_cases_count:        int            = 0     # injected by service layer

    # ── Ordering / Audit ──────────────────────────────────────────────────────
    display_order:             int            = 0
    created_at:                datetime
    updated_at:                Optional[datetime] = None  # FIX 4: Optional + default
    modified_by_name:          Optional[str]  = None

    # ── FIX 1: Parse required_documents JSON string → list ───────────────────
    @field_validator("required_documents", mode="before")
    @classmethod
    def parse_required_documents(cls, v):
        """
        DB stores required_documents as a JSON string e.g.
        '["Passport Copy", "Offer Letter"]'
        This validator runs BEFORE Pydantic checks the type,
        converting the string to a list so validation passes.
        """
        if v is None:
            return []
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, TypeError):
                return []
        if isinstance(v, list):
            return v
        return []

    # ── FIX 3: Derive status from is_active when no DB column exists ──────────
    @field_validator("status", mode="before")
    @classmethod
    def derive_status(cls, v):
        """
        VisaType ORM model has no status column — only is_active.
        Service layer can pass status explicitly if needed.
        If missing/None, model_post_init fills it from is_active.
        """
        if v in (None, ""):
            return None
        return v

    def model_post_init(self, __context: Any) -> None:
        """
        Runs AFTER all field validators succeed.
        1. Fill status from is_active if still None
        2. Set required_documents_count from the already-parsed list
        """
        # 1. Derive status
        if self.status is None:
            object.__setattr__(
                self, "status",
                "active" if self.is_active else "inactive"
            )

        # 2. Count required docs (list already parsed by field_validator above)
        docs = self.required_documents
        if isinstance(docs, list):
            object.__setattr__(self, "required_documents_count", len(docs))


# =============================================================================
# LIST RESPONSE — paginated grid + KPI stats in one request
# GET /admin/visa-types
# =============================================================================

class VisaTypeStats(BaseModel):
    """
    Powers the 4 KPI cards at the top of the screen:
      - "52 Total Visa Types    ↑12%"
      - "48 Active Visa Types   ↑8%"
      - "4  Pending Review      —0%"
      - "3,247 Active Cases     ↑24%"
    """
    total_visa_types:  int
    active_visa_types: int
    pending_review:    int
    active_cases:      int

    # percentage change labels shown in UI (e.g. "+12%")
    total_pct_change:   Optional[int] = None
    active_pct_change:  Optional[int] = None
    pending_pct_change: Optional[int] = None
    cases_pct_change:   Optional[int] = None


class VisaTypeListResponse(BaseModel):
    """
    Single response that drives the entire Visa Types Manager page.
    Frontend gets stats + items in one call — no waterfall.
    """
    stats:       VisaTypeStats
    items:       List[VisaTypeResponse]
    total:       int
    page:        int = 1
    page_size:   int = 20
    total_pages: int = 1


# =============================================================================
# EXPORT RESPONSE
# GET /admin/visa-types/export
# Powers the "Export All" button — returns CSV bytes via StreamingResponse
# Schema below is for the JSON export variant (same endpoint, Accept header)
# =============================================================================

class VisaTypeExportRow(BaseModel):
    """One row in the exported spreadsheet."""
    code:                      str
    name:                      str
    category:                  str
    status:                    Optional[str]
    requires_employer_sponsor: bool
    required_documents_count:  int
    typical_processing_days:   Optional[int]
    government_fee_usd:        Optional[int]
    success_rate:              Optional[int]
    active_cases_count:        int
    is_active:                 bool
    created_at:                str
    updated_at:                str
