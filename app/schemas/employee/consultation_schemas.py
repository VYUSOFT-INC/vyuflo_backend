# =============================================================================
# app/schemas/consultation_schemas.py
# Pydantic v2 schemas for consultation tables 58-61
# =============================================================================

from __future__ import annotations

import uuid
from datetime import date, time, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, field_validator


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# User nested inside AttorneyProfile
# =============================================================================

class UserBriefOut(ORMBase):
    id:         uuid.UUID
    first_name: str
    last_name:  str
    email:      str
    phone:      Optional[str]


# =============================================================================
# AttorneyProfile (TABLE 42 — already in models)
# =============================================================================

class AttorneyProfileOut(ORMBase):
    id:                uuid.UUID
    user_id:           uuid.UUID
    bar_number:        Optional[str]
    bar_state:         Optional[str]
    years_experience:  Optional[int]
    law_firm_name:     Optional[str]
    specialisations:   Optional[str]
    languages:         Optional[str]
    availability_note: Optional[str]
    max_active_cases:  Optional[int]
    bio:               Optional[str]
    profile_photo_url: Optional[str]
    is_accepting_cases: bool
    is_verified:       bool
    is_active:         bool
    created_at:        datetime
    updated_at:        datetime
    user:              Optional[UserBriefOut] = None


# =============================================================================
# AppointmentType (TABLE 58)
# =============================================================================

class AppointmentTypeOut(ORMBase):
    id:               uuid.UUID
    title:            str
    description:      Optional[str]
    duration_minutes: int
    price_usd:        int        # US cents
    is_active:        bool
    sort_order:       int


class AppointmentTypeCreateRequest(BaseModel):
    title:            str
    description:      Optional[str] = None
    duration_minutes: int
    price_usd:        int           # US cents
    sort_order:       int = 0


# =============================================================================
# AttorneyAvailability (TABLE 59)
# =============================================================================

class AttorneyAvailabilityOut(ORMBase):
    id:                    uuid.UUID
    attorney_id:           uuid.UUID
    day_of_week:           int        # 0=Mon … 6=Sun
    start_time:            time
    end_time:              time
    slot_duration_minutes: int
    timezone:              str
    is_active:             bool


class AttorneyAvailabilityCreateRequest(BaseModel):
    day_of_week:           int
    start_time:            time
    end_time:              time
    slot_duration_minutes: int = 30
    timezone:              str = "America/Los_Angeles"

    @field_validator("day_of_week")
    @classmethod
    def valid_day(cls, v: int) -> int:
        if v not in range(7):
            raise ValueError("day_of_week must be 0–6")
        return v


# =============================================================================
# ConsultationSlot (TABLE 60)
# =============================================================================

class ConsultationSlotOut(ORMBase):
    id:         uuid.UUID
    attorney_id: uuid.UUID
    slot_date:  date
    slot_time:  time
    timezone:   str
    is_booked:  bool
    is_blocked: bool

    # Virtual field for the frontend — computed in service
    availability: str = "high"   # "high" | "limited" | "none"


class SlotGenerateRequest(BaseModel):
    """Admin/attorney generates slots for a date range."""
    attorney_id: uuid.UUID
    from_date:   date
    to_date:     date


# =============================================================================
# ConsultationBooking (TABLE 61)
# =============================================================================

class ConsultationBookingOut(ORMBase):
    id:                  uuid.UUID
    employee_id:         uuid.UUID
    attorney_id:         uuid.UUID
    slot_id:             uuid.UUID
    appointment_type_id: uuid.UUID
    consultation_format: str
    status:              str
    amount_usd:          Optional[int]
    is_paid:             bool
    meeting_link:        Optional[str]
    employee_notes:      Optional[str]
    attorney_notes:      Optional[str]
    cancellation_reason: Optional[str]
    cancelled_at:        Optional[datetime]
    created_at:          datetime
    updated_at:          datetime

    # Nested
    appointment_type: Optional[AppointmentTypeOut] = None
    slot:             Optional[ConsultationSlotOut] = None
    attorney:         Optional[AttorneyProfileOut]  = None


class CreateConsultationBookingRequest(BaseModel):
    attorney_id:          uuid.UUID
    appointment_type_id:  uuid.UUID
    consultation_format:  str = "virtual"
    slot_id:              uuid.UUID
    employee_notes:       Optional[str] = None

    @field_validator("consultation_format")
    @classmethod
    def valid_format(cls, v: str) -> str:
        if v not in ("virtual", "in_person"):
            raise ValueError("consultation_format must be 'virtual' or 'in_person'")
        return v


class CreateConsultationBookingResponse(BaseModel):
    id:      uuid.UUID
    status:  str
    message: Optional[str] = None


class CancelBookingRequest(BaseModel):
    reason: Optional[str] = None


# =============================================================================
# Book-page aggregate — what the frontend loads in one call
# =============================================================================

class BookConsultationPageData(BaseModel):
    """
    GET /api/v1/consultations/book-page?attorney_id=xxx
    Returns everything the BookConsultation screen needs in a single request.
    """
    attorney:          Optional[AttorneyProfileOut]
    appointment_types: List[AppointmentTypeOut]
    slots:             List[ConsultationSlotOut]