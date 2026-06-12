"""
intake_service.py
Path: app/services/attorney/intake_service.py

V1 service layer — Client Intake Form + Client Profile (Screen 26).
Same conventions as role_service.py.

Key fixes vs previous version:
  • Models imported from app.models.visamodels (where they actually live)
  • Application.due_date used correctly (Date column, not deadline_date)
  • Application.application_number used for case_number (not id slice)
  • Application.progress_percent + current_stage used for active case card
  • Application.visa_type relationship used for visa_type_name
  • Application.sponsor_employer used where employer needed later
  • Fee.amount_usd is in CENTS → divided by 100 for dollar display
  • Billing sourced from fees table (real data)
  • Next deadline sourced from deadlines table (not application.due_date)
  • Recent activity sourced from audit_logs table (real data)
  • passport_expiry_date flows through save + get
"""

from __future__ import annotations

import json
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.services import db_create, db_get_by_id, db_update
from app.models.visamodels import (
    Application,
    AuditLog,
    ClientIntakeSession,
    Deadline,
    Fee,
    IntakeImmigrationHistory,
    User,
)
from app.schemas.attorney.intake import (
    ActiveCaseSnapshot,
    ActivityItem,
    BillingSummarySnapshot,
    ClientProfileResponse,
    GenerateLinkResponse,
    IntakeDataResponse,
    IntakeDataSave,
    IntakeSessionCreate,
    IntakeSessionResponse,
    PreviousVisaItem,
    SaveDraftResponse,
    SubmitIntakeResponse,
    VisaStatusOption,
    VisaStatusOptionsResponse,
)

TOKEN_EXPIRY_DAYS      = 7
CLIENT_PORTAL_BASE_URL = "https://app.visaflow.com/intake"

VISA_STATUS_OPTIONS = [
    ("H1B",               "H-1B Specialty Occupation"),
    ("H4",                "H-4 Dependent"),
    ("L1",                "L-1 Intracompany Transfer"),
    ("L2",                "L-2 Dependent"),
    ("O1",                "O-1 Extraordinary Ability"),
    ("TN",                "TN NAFTA Professional"),
    ("F1",                "F-1 Student"),
    ("F2",                "F-2 Student Dependent"),
    ("J1",                "J-1 Exchange Visitor"),
    ("J2",                "J-2 Exchange Visitor Dependent"),
    ("B1_B2",             "B-1/B-2 Visitor"),
    ("E3",                "E-3 Australian Professional"),
    ("Green_Card",        "Permanent Resident (Green Card)"),
    ("US_Citizen",        "U.S. Citizen"),
    ("Unlawful_Presence", "Unlawful Presence"),
    ("No_Visa",           "No Visa / Never Entered"),
    ("Other",             "Other"),
]

# Application statuses considered "active" for Screen 26 stats ribbon
ACTIVE_STATUSES = ("in_progress", "action_needed", "rfe_response", "draft")


# ===========================================================================
# INTERNAL HELPERS
# ===========================================================================

async def _get_session_or_404(
    db: AsyncSession, session_id: uuid.UUID
) -> ClientIntakeSession:
    session = await db_get_by_id(db, ClientIntakeSession, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Intake session {session_id} not found.",
        )
    return session


async def _fetch_intake_row(
    db: AsyncSession, session_id: uuid.UUID
) -> Optional[IntakeImmigrationHistory]:
    result = await db.execute(
        select(IntakeImmigrationHistory).where(
            IntakeImmigrationHistory.intake_session_id == session_id
        )
    )
    return result.scalars().first()


def _parse_previous_visas(raw: Optional[str]) -> List[PreviousVisaItem]:
    if not raw:
        return []
    try:
        return [PreviousVisaItem(**item) for item in json.loads(raw)]
    except Exception:
        return []


def _serialize_previous_visas(visas: List[PreviousVisaItem]) -> str:
    return json.dumps([v.model_dump(mode="json") for v in visas])


def _build_intake_data_response(row: IntakeImmigrationHistory) -> IntakeDataResponse:
    return IntakeDataResponse(
        id                   = row.id,
        intake_session_id    = row.intake_session_id,
        first_name           = row.first_name,
        last_name            = row.last_name,
        date_of_birth        = row.date_of_birth,
        gender               = row.gender,
        nationality          = row.nationality,
        passport_number      = row.passport_number,
        passport_expiry_date = row.passport_expiry_date,
        email                = row.email,
        current_visa_status  = row.current_visa_status,
        visa_expiration_date = row.visa_expiration_date,
        has_visa_denial      = row.has_visa_denial,
        visa_denial_details  = row.visa_denial_details,
        has_overstay         = row.has_overstay,
        previous_visas       = _parse_previous_visas(row.previous_visas),
        created_at           = row.created_at,
        updated_at           = row.updated_at,
    )


def _build_session_response(
    session: ClientIntakeSession,
    intake_data: Optional[IntakeImmigrationHistory] = None,
) -> IntakeSessionResponse:
    return IntakeSessionResponse(
        id               = session.id,
        application_id   = session.application_id,
        token            = session.token,
        token_expires_at = session.token_expires_at,
        current_step     = session.current_step,
        step_1_completed = session.step_1_completed,
        step_2_completed = session.step_2_completed,
        step_3_completed = session.step_3_completed,
        step_4_completed = session.step_4_completed,
        step_5_completed = session.step_5_completed,
        is_draft         = session.is_draft,
        last_saved_at    = session.last_saved_at,
        is_submitted     = session.is_submitted,
        submitted_at     = session.submitted_at,
        created_at       = session.created_at,
        updated_at       = session.updated_at,
        intake_data      = _build_intake_data_response(intake_data) if intake_data else None,
    )


# ===========================================================================
# VISA STATUS OPTIONS
# ===========================================================================

def get_visa_status_options() -> VisaStatusOptionsResponse:
    return VisaStatusOptionsResponse(
        items=[VisaStatusOption(value=v, label=l) for v, l in VISA_STATUS_OPTIONS]
    )


# ===========================================================================
# SESSION — create
# ===========================================================================
async def create_session(
    db: AsyncSession,
    payload: IntakeSessionCreate,
    current_user_id: uuid.UUID,
) -> IntakeSessionResponse:

    # Check application exists
    application = await db.get(Application, payload.application_id)

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {payload.application_id} not found."
        )

    # Check session already exists
    existing = await db.execute(
        select(ClientIntakeSession).where(
            ClientIntakeSession.application_id == payload.application_id
        )
    )

    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Intake session already exists for this application."
        )

    new_session = ClientIntakeSession(
        application_id=payload.application_id,
        current_step=1,
        is_draft=True,
        created_by=current_user_id,
    )

    if payload.generate_link:
        new_session.token = secrets.token_urlsafe(64)
        new_session.token_expires_at = (
            datetime.now(timezone.utc) +
            timedelta(days=TOKEN_EXPIRY_DAYS)
        )
        new_session.token_generated_by = current_user_id
        new_session.token_generated_at = datetime.now(timezone.utc)

    new_session = await db_create(db, new_session)

    return _build_session_response(new_session)


# ===========================================================================
# SESSION — get by ID (attorney)
# ===========================================================================

async def get_session(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> IntakeSessionResponse:
    session    = await _get_session_or_404(db, session_id)
    intake_row = await _fetch_intake_row(db, session_id)
    return _build_session_response(session, intake_row)


# ===========================================================================
# SESSION — get by token (client portal, no JWT)
# ===========================================================================

async def get_session_by_token(
    db: AsyncSession,
    token: str,
) -> IntakeSessionResponse:
    result = await db.execute(
        select(ClientIntakeSession).where(ClientIntakeSession.token == token)
    )
    session = result.scalars().first()

    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid or expired intake link.")
    if session.token_expires_at and session.token_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="This intake link has expired. Ask your attorney to regenerate it.")

    intake_row = await _fetch_intake_row(db, session.id)
    return _build_session_response(session, intake_row)


# ===========================================================================
# GENERATE CLIENT LINK
# ===========================================================================

async def generate_client_link(
    db: AsyncSession,
    session_id: uuid.UUID,
    current_user_id: uuid.UUID,
) -> GenerateLinkResponse:
    await _get_session_or_404(db, session_id)

    token      = secrets.token_urlsafe(64)
    expires_at = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRY_DAYS)

    await db_update(db, ClientIntakeSession, session_id, {
        "token":               token,
        "token_expires_at":    expires_at,
        "token_generated_by":  current_user_id,
        "token_generated_at":  datetime.now(timezone.utc),
        "modified_by":         current_user_id,
    })

    return GenerateLinkResponse(
        token            = token,
        client_url       = f"{CLIENT_PORTAL_BASE_URL}/{token}",
        token_expires_at = expires_at,
    )


# ===========================================================================
# INTAKE DATA — save (upsert)
# ===========================================================================

async def save_intake_data(
    db: AsyncSession,
    session_id: uuid.UUID,
    payload: IntakeDataSave,
    current_user_id: uuid.UUID,
    step_completed: Optional[int] = None,
) -> IntakeDataResponse:
    if payload.has_visa_denial is True and not payload.visa_denial_details:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="visa_denial_details is required when has_visa_denial is True.",
        )

    session = await _get_session_or_404(db, session_id)
    row     = await _fetch_intake_row(db, session_id)

    data = payload.model_dump(exclude_unset=True)

    if "previous_visas" in data and data["previous_visas"] is not None:
        data["previous_visas"] = _serialize_previous_visas(payload.previous_visas)

    data["modified_by"] = current_user_id

    if row:
        row = await db_update(db, IntakeImmigrationHistory, row.id, data)
    else:
        row = IntakeImmigrationHistory(
            intake_session_id = session_id,
            created_by        = current_user_id,
            **{k: v for k, v in data.items() if k != "modified_by"},
        )
        row = await db_create(db, row)

    session_update: dict = {
        "last_saved_at": datetime.now(timezone.utc),
        "modified_by":   current_user_id,
    }
    if step_completed == 1:
        session_update["step_1_completed"] = True
        session_update["current_step"]     = max(session.current_step, 2)
    elif step_completed == 3:
        session_update["step_3_completed"] = True
        session_update["current_step"]     = max(session.current_step, 4)

    await db_update(db, ClientIntakeSession, session_id, session_update)
    return _build_intake_data_response(row)


# ===========================================================================
# INTAKE DATA — get
# ===========================================================================

async def get_intake_data(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> Optional[IntakeDataResponse]:
    await _get_session_or_404(db, session_id)
    row = await _fetch_intake_row(db, session_id)
    return _build_intake_data_response(row) if row else None


# ===========================================================================
# SAVE DRAFT
# ===========================================================================

async def save_draft(
    db: AsyncSession,
    session_id: uuid.UUID,
    current_user_id: uuid.UUID,
) -> SaveDraftResponse:
    now     = datetime.now(timezone.utc)
    updated = await db_update(db, ClientIntakeSession, session_id, {
        "is_draft":      True,
        "last_saved_at": now,
        "modified_by":   current_user_id,
    })
    return SaveDraftResponse(
        detail        = "Draft saved successfully.",
        last_saved_at = now,
        current_step  = updated.current_step,
    )


# ===========================================================================
# SUBMIT
# ===========================================================================

async def submit_intake(
    db: AsyncSession,
    session_id: uuid.UUID,
    current_user_id: uuid.UUID,
) -> SubmitIntakeResponse:
    session = await _get_session_or_404(db, session_id)

    if session.is_submitted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This intake form has already been submitted.",
        )

    now = datetime.now(timezone.utc)
    await db_update(db, ClientIntakeSession, session_id, {
        "is_submitted": True,
        "submitted_at": now,
        "is_draft":     False,
        "modified_by":  current_user_id,
    })

    return SubmitIntakeResponse(
        detail       = "Intake form submitted successfully.",
        submitted_at = now,
        session_id   = session_id,
    )


# ===========================================================================
# CLIENT PROFILE — Screen 26
# ===========================================================================

async def get_client_profile(
    db: AsyncSession,
    client_id: uuid.UUID,
) -> ClientProfileResponse:
    """
    GET /clients/{client_id}/profile — Screen 26 aggregated view.

    Data sources (all from visamodels.py):
      users                       → name, email, phone, created_at
      applications                → total_cases, active_cases, active case card
      deadlines                   → next_deadline_days
      fees                        → billing_summary (amount_usd is cents)
      audit_logs                  → recent_activity (last 3)
      intake_immigration_history  → visa status, nationality, passport details
    """

    # ── 1. Load user ──────────────────────────────────────────────────────────
    user = await db_get_by_id(db, User, client_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_id} not found.",
        )

    first_name = user.first_name or ""
    last_name  = user.last_name  or ""
    full_name  = f"{first_name} {last_name}".strip() or user.email
    initials   = (
        (first_name[0] if first_name else "") +
        (last_name[0]  if last_name  else "")
    ).upper() or "?"

    # ── 2. Application counts ─────────────────────────────────────────────────
    total_result = await db.execute(
        select(func.count(Application.id)).where(Application.user_id == client_id)
    )
    total_cases = total_result.scalar_one() or 0

    active_result = await db.execute(
        select(func.count(Application.id)).where(
            Application.user_id == client_id,
            Application.status.in_(ACTIVE_STATUSES),
        )
    )
    active_cases = active_result.scalar_one() or 0

    # ── 3. Most recent active application ────────────────────────────────────
    app_result = await db.execute(
        select(Application)
        .where(
            Application.user_id == client_id,
            Application.status.in_(ACTIVE_STATUSES),
        )
        .order_by(Application.created_at.desc())
        .limit(1)
    )
    active_app = app_result.scalars().first()

    # ── 4. Active case snapshot ───────────────────────────────────────────────
    active_case_snapshot: Optional[ActiveCaseSnapshot] = None
    if active_app:
        visa_name = None
        if active_app.visa_type:
            visa_name = getattr(active_app.visa_type, "name", None) \
                     or getattr(active_app.visa_type, "code", None)

        active_case_snapshot = ActiveCaseSnapshot(
            case_id          = active_app.id,
            case_number      = active_app.application_number,
            visa_type_name   = visa_name,
            status           = active_app.status,
            progress_percent = active_app.progress_percent,
            current_stage    = active_app.current_stage,
            due_date         = active_app.due_date,
        )

    # ── 5. Next deadline (from deadlines table) ───────────────────────────────
    next_deadline_days: Optional[int] = None
    deadline_result = await db.execute(
        select(Deadline)
        .where(
            Deadline.user_id      == client_id,
            Deadline.is_completed == False,
            Deadline.is_dismissed == False,
        )
        .order_by(Deadline.due_date.asc())
        .limit(1)
    )
    nearest_deadline = deadline_result.scalars().first()
    if nearest_deadline:
        delta = (nearest_deadline.due_date.date() - date.today()).days
        next_deadline_days = max(delta, 0)

    # ── 6. Billing summary (fees table, amount_usd in cents) ─────────────────
    fees_result = await db.execute(
        select(Fee).where(Fee.user_id == client_id)
    )
    all_fees = fees_result.scalars().all()

    total_billed = sum(f.amount_usd for f in all_fees
                       if f.status not in ("waived", "cancelled")) / 100
    total_paid   = sum(f.amount_usd for f in all_fees
                       if f.status == "paid") / 100
    outstanding  = round(total_billed - total_paid, 2)

    # ── 7. Recent activity (last 3 audit_log entries for this user) ───────────
    activity_result = await db.execute(
        select(AuditLog)
        .where(AuditLog.actor_id == client_id)
        .order_by(AuditLog.created_at.desc())
        .limit(3)
    )
    activity_rows = activity_result.scalars().all()
    recent_activity = [
        ActivityItem(
            action      = row.action,
            description = row.description,
            occurred_at = row.created_at,
        )
        for row in activity_rows
    ]

    # ── 8. Intake data (visa status, nationality, passport) ───────────────────
    intake_row: Optional[IntakeImmigrationHistory] = None
    if active_app:
        session_result = await db.execute(
            select(ClientIntakeSession).where(
                ClientIntakeSession.application_id == active_app.id
            )
        )
        intake_session = session_result.scalars().first()
        if intake_session:
            intake_row = await _fetch_intake_row(db, intake_session.id)

    return ClientProfileResponse(
        # Hero
        client_id            = user.id,
        full_name            = full_name,
        initials             = initials,
        email                = user.email,
        phone                = user.phone,
        current_visa_status  = getattr(intake_row, "current_visa_status",  None),
        location             = None,   # V1: skipped
        employer             = None,   # V1: skipped
        job_title            = None,   # V1: skipped
        client_since         = user.created_at,

        # Contact & Details
        nationality          = getattr(intake_row, "nationality",          None),
        passport_number      = getattr(intake_row, "passport_number",      None),
        passport_expiry_date = getattr(intake_row, "passport_expiry_date", None),

        # Stats ribbon
        total_cases          = total_cases,
        active_cases         = active_cases,
        unbilled_amount      = outstanding,
        next_deadline_days   = next_deadline_days,

        # Overview cards
        active_case          = active_case_snapshot,
        billing_summary      = BillingSummarySnapshot(
            total_billed = total_billed,
            total_paid   = total_paid,
            outstanding  = outstanding,
        ),
        recent_activity      = recent_activity,
    )
