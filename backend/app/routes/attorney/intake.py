"""
intake.py  (router)
Path: app/routers/attorney/intake.py

V1 routes — Client Intake Form + Client Profile (Screen 26).
10 endpoints total.

Import paths match the user's actual project structure:
  app.services.attorney.intake_service
  app.schemas.attorney.intake
  app.models.visamodels
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.core_permissions import get_current_user, get_db
from app.models.visamodels import User
from app.services.attorney import intake_service
from app.schemas.attorney.intake import (
    ClientProfileResponse,
    GenerateLinkResponse,
    IntakeDataResponse,
    IntakeDataSave,
    IntakeSessionCreate,
    IntakeSessionResponse,
    SaveDraftResponse,
    SubmitIntakeResponse,
    VisaStatusOptionsResponse,
)

intake_router = APIRouter(tags=["Client Intake Form"])


# ===========================================================================
# UTILITY — no auth needed
# ===========================================================================

@intake_router.get(
    "/intake/visa-status-options",
    response_model=VisaStatusOptionsResponse,
    summary="Current Visa Status dropdown (Screen 03)",
)
async def get_visa_status_options():
    """Populates the 'Current Visa Status' dropdown on Screen 03."""
    return intake_service.get_visa_status_options()


# ===========================================================================
# CLIENT PORTAL — token access, no JWT
# ===========================================================================

@intake_router.get(
    "/intake/by-token/{token}",
    response_model=IntakeSessionResponse,
    summary="Client loads intake form via secure link — no JWT (Screen 04)",
)
async def get_session_by_token(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Screen 04 — client clicks emailed link.
    No JWT. Token validated for existence + 7-day expiry.
    """
    return await intake_service.get_session_by_token(db, token)


# ===========================================================================
# SESSION
# ===========================================================================

@intake_router.post(
    "/intake/sessions",
    response_model=IntakeSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create intake session for an application",
)
async def create_session(
    payload: IntakeSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Attorney creates a session. Pass generate_link=true to create the
    client token in the same call. 409 if session already exists.
    """
    return await intake_service.create_session(db, payload, current_user.user_id)


@intake_router.get(
    "/intake/sessions/{session_id}",
    response_model=IntakeSessionResponse,
    summary="Get session with all step data",
)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns session + embedded intake_data (null if not yet saved)."""
    return await intake_service.get_session(db, session_id)


@intake_router.post(
    "/intake/sessions/{session_id}/generate-link",
    response_model=GenerateLinkResponse,
    summary="Generate or rotate client link — Screen 03 'Generate Link' button",
)
async def generate_client_link(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Rotates token each call. Token valid 7 days.
    Returns full client URL for emailing.
    """
    return await intake_service.generate_client_link(db, session_id, current_user.user_id)


@intake_router.post(
    "/intake/sessions/{session_id}/save-draft",
    response_model=SaveDraftResponse,
    summary="Save Draft — Screen 03 top-right button",
)
async def save_draft(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stamps last_saved_at. Step data saved separately via PUT /data."""
    return await intake_service.save_draft(db, session_id, current_user.user_id)


@intake_router.post(
    "/intake/sessions/{session_id}/submit",
    response_model=SubmitIntakeResponse,
    summary="Final submit — Step 5 Review screen",
)
async def submit_intake(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Locks the session. Returns 409 if already submitted."""
    return await intake_service.submit_intake(db, session_id, current_user.user_id)


# ===========================================================================
# INTAKE DATA — single endpoint covers Step 1 (Screen 04) + Step 3 (Screen 03)
# ===========================================================================

@intake_router.get(
    "/intake/sessions/{session_id}/data",
    response_model=IntakeDataResponse,
    summary="Load intake data — Step 1 + Step 3 fields",
)
async def get_intake_data(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Called on page load to pre-fill fields from a saved draft.
    Returns 204 No Content on first visit (nothing saved yet).
    """
    result = await intake_service.get_intake_data(db, session_id)
    if result is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return result


@intake_router.put(
    "/intake/sessions/{session_id}/data",
    response_model=IntakeDataResponse,
    summary="Save intake data — auto-save, Save Draft, or Continue",
)
async def save_intake_data(
    session_id: uuid.UUID,
    payload: IntakeDataSave,
    step_completed: Optional[int] = Query(
        default=None,
        ge=1,
        le=5,
        description=(
            "Pass the step number when 'Continue' is clicked. "
            "Omit for auto-save or Save Draft."
        ),
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    One endpoint, three scenarios:

    | UI action             | step_completed |
    |-----------------------|----------------|
    | Auto-save on blur     | omit           |
    | 'Save Draft' button   | omit           |
    | 'Continue' Step 1     | 1              |
    | 'Continue' Step 3     | 3              |

    Only send changed fields. previous_visas replaces the full list.
    Validates: visa_denial_details required if has_visa_denial=True.
    """
    return await intake_service.save_intake_data(
        db, session_id, payload, current_user.user_id, step_completed
    )


# ===========================================================================
# CLIENT PROFILE — Screen 26
# ===========================================================================

@intake_router.get(
    "/clients/{client_id}/profile",
    response_model=ClientProfileResponse,
    summary="Client Profile page — Screen 26 aggregated view",
)
async def get_client_profile(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Screen 26 — attorney views a client's full profile.

    Aggregates from: users, applications, deadlines,
                     fees, audit_logs, intake_immigration_history.

    V1 nulls (future sprints):
      location / employer / job_title → always null
    """
    return await intake_service.get_client_profile(db, client_id)
