# """
# intake_service.py
# Path: app/services/attorney/intake_service.py

# V1 service layer — Client Intake Form + Client Profile (Screen 26).
# Same conventions as role_service.py.

# Key fixes vs previous version:
#   • Models imported from app.models.visamodels (where they actually live)
#   • Application.due_date used correctly (Date column, not deadline_date)
#   • Application.application_number used for case_number (not id slice)
#   • Application.progress_percent + current_stage used for active case card
#   • Application.visa_type relationship used for visa_type_name
#   • Application.sponsor_employer used where employer needed later
#   • Fee.amount_usd is in CENTS → divided by 100 for dollar display
#   • Billing sourced from fees table (real data)
#   • Next deadline sourced from deadlines table (not application.due_date)
#   • Recent activity sourced from audit_logs table (real data)
#   • passport_expiry_date flows through save + get
# """

from __future__ import annotations

import json
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings          # NEW
from app.core.email import send_email  

from app.services.employee.services import db_create, db_get_by_id, db_update
from app.models.visamodels import (
    Application,
    AuditLog,
    ClientIntakeSession,
    Deadline,
    Fee,
    IntakeImmigrationHistory,
    Notification,
    User,
)
from app.schemas.attorney.intake import (
    AcceptIntakeRequest,               # ← ADD THIS
    ActiveCaseSnapshot,
    ActivityItem,
    AssignedApplicationResponse,
    BillingSummarySnapshot,
    ClientProfileResponse,
    GenerateLinkResponse,
    IntakeDataResponse,
    IntakeDataSave,
    IntakeReviewDecisionResponse,
    IntakeSessionCreate,
    IntakeSessionResponse,
    PreviousVisaItem,
    RequestIntakeChangesRequest,
    SaveDraftResponse,
    SubmitIntakeResponse,
    VerifyDisclosuresResponse,
    VisaStatusOption,
    VisaStatusOptionsResponse,
)

# TOKEN_EXPIRY_DAYS      = 7
# CLIENT_PORTAL_BASE_URL = "https://app.visaflow.com/intake"

# VISA_STATUS_OPTIONS = [
#     ("H1B",               "H-1B Specialty Occupation"),
#     ("H4",                "H-4 Dependent"),
#     ("L1",                "L-1 Intracompany Transfer"),
#     ("L2",                "L-2 Dependent"),
#     ("O1",                "O-1 Extraordinary Ability"),
#     ("TN",                "TN NAFTA Professional"),
#     ("F1",                "F-1 Student"),
#     ("F2",                "F-2 Student Dependent"),
#     ("J1",                "J-1 Exchange Visitor"),
#     ("J2",                "J-2 Exchange Visitor Dependent"),
#     ("B1_B2",             "B-1/B-2 Visitor"),
#     ("E3",                "E-3 Australian Professional"),
#     ("Green_Card",        "Permanent Resident (Green Card)"),
#     ("US_Citizen",        "U.S. Citizen"),
#     ("Unlawful_Presence", "Unlawful Presence"),
#     ("No_Visa",           "No Visa / Never Entered"),
#     ("Other",             "Other"),
# ]

# # Application statuses considered "active" for Screen 26 stats ribbon
# ACTIVE_STATUSES = ("in_progress", "action_needed", "rfe_response", "draft")


# # ===========================================================================
# # INTERNAL HELPERS
# # ===========================================================================

# async def _get_session_or_404(
#     db: AsyncSession, session_id: uuid.UUID
# ) -> ClientIntakeSession:
#     session = await db_get_by_id(db, ClientIntakeSession, session_id)
#     if not session:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Intake session {session_id} not found.",
#         )
#     return session


# async def _fetch_intake_row(
#     db: AsyncSession, session_id: uuid.UUID
# ) -> Optional[IntakeImmigrationHistory]:
#     result = await db.execute(
#         select(IntakeImmigrationHistory).where(
#             IntakeImmigrationHistory.intake_session_id == session_id
#         )
#     )
#     return result.scalars().first()


# def _parse_previous_visas(raw: Optional[str]) -> List[PreviousVisaItem]:
#     if not raw:
#         return []
#     try:
#         return [PreviousVisaItem(**item) for item in json.loads(raw)]
#     except Exception:
#         return []


# def _serialize_previous_visas(visas: List[PreviousVisaItem]) -> str:
#     return json.dumps([v.model_dump(mode="json") for v in visas])


# def _build_intake_data_response(row: IntakeImmigrationHistory) -> IntakeDataResponse:
#     return IntakeDataResponse(
#         id                   = row.id,
#         intake_session_id    = row.intake_session_id,
#         first_name           = row.first_name,
#         last_name            = row.last_name,
#         date_of_birth        = row.date_of_birth,
#         gender               = row.gender,
#         nationality          = row.nationality,
#         passport_number      = row.passport_number,
#         passport_expiry_date = row.passport_expiry_date,
#         email                = row.email,
#         current_visa_status  = row.current_visa_status,
#         visa_expiration_date = row.visa_expiration_date,
#         has_visa_denial      = row.has_visa_denial,
#         visa_denial_details  = row.visa_denial_details,
#         has_overstay         = row.has_overstay,
#         previous_visas       = _parse_previous_visas(row.previous_visas),
#         created_at           = row.created_at,
#         updated_at           = row.updated_at,
#     )


# def _build_session_response(
#     session: ClientIntakeSession,
#     intake_data: Optional[IntakeImmigrationHistory] = None,
# ) -> IntakeSessionResponse:
#     return IntakeSessionResponse(
#         id               = session.id,
#         application_id   = session.application_id,
#         token            = session.token,
#         token_expires_at = session.token_expires_at,
#         current_step     = session.current_step,
#         step_1_completed = session.step_1_completed,
#         step_2_completed = session.step_2_completed,
#         step_3_completed = session.step_3_completed,
#         step_4_completed = session.step_4_completed,
#         step_5_completed = session.step_5_completed,
#         is_draft         = session.is_draft,
#         last_saved_at    = session.last_saved_at,
#         is_submitted     = session.is_submitted,
#         submitted_at     = session.submitted_at,
#         created_at       = session.created_at,
#         updated_at       = session.updated_at,
#         intake_data      = _build_intake_data_response(intake_data) if intake_data else None,
#     )


# # ===========================================================================
# # VISA STATUS OPTIONS
# # ===========================================================================

# def get_visa_status_options() -> VisaStatusOptionsResponse:
#     return VisaStatusOptionsResponse(
#         items=[VisaStatusOption(value=v, label=l) for v, l in VISA_STATUS_OPTIONS]
#     )


# # ===========================================================================
# # SESSION — create
# # ===========================================================================

# async def create_session(
#     db: AsyncSession,
#     payload: IntakeSessionCreate,
#     current_user_id: uuid.UUID,
# ) -> IntakeSessionResponse:
#     existing = await db.execute(
#         select(ClientIntakeSession).where(
#             ClientIntakeSession.application_id == payload.application_id
#         )
#     )
#     if existing.scalars().first():
#         raise HTTPException(
#             status_code=status.HTTP_409_CONFLICT,
#             detail="Intake session already exists for this application.",
#         )

#     new_session = ClientIntakeSession(
#         application_id = payload.application_id,
#         current_step   = 1,
#         is_draft       = True,
#         created_by     = current_user_id,
#     )

#     if payload.generate_link:
#         new_session.token              = secrets.token_urlsafe(64)
#         new_session.token_expires_at   = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRY_DAYS)
#         new_session.token_generated_by = current_user_id
#         new_session.token_generated_at = datetime.now(timezone.utc)

#     new_session = await db_create(db, new_session)
#     return _build_session_response(new_session)


# # ===========================================================================
# # SESSION — get by ID (attorney)
# # ===========================================================================

# async def get_session(
#     db: AsyncSession,
#     session_id: uuid.UUID,
# ) -> IntakeSessionResponse:
#     session    = await _get_session_or_404(db, session_id)
#     intake_row = await _fetch_intake_row(db, session_id)
#     return _build_session_response(session, intake_row)


# # ===========================================================================
# # SESSION — get by token (client portal, no JWT)
# # ===========================================================================

# async def get_session_by_token(
#     db: AsyncSession,
#     token: str,
# ) -> IntakeSessionResponse:
#     result = await db.execute(
#         select(ClientIntakeSession).where(ClientIntakeSession.token == token)
#     )
#     session = result.scalars().first()

#     if not session:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
#                             detail="Invalid or expired intake link.")
#     if session.token_expires_at and session.token_expires_at < datetime.now(timezone.utc):
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
#                             detail="This intake link has expired. Ask your attorney to regenerate it.")

#     intake_row = await _fetch_intake_row(db, session.id)
#     return _build_session_response(session, intake_row)


# # ===========================================================================
# # GENERATE CLIENT LINK
# # ===========================================================================

# async def generate_client_link(
#     db: AsyncSession,
#     session_id: uuid.UUID,
#     current_user_id: uuid.UUID,
# ) -> GenerateLinkResponse:
#     await _get_session_or_404(db, session_id)

#     token      = secrets.token_urlsafe(64)
#     expires_at = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRY_DAYS)

#     await db_update(db, ClientIntakeSession, session_id, {
#         "token":               token,
#         "token_expires_at":    expires_at,
#         "token_generated_by":  current_user_id,
#         "token_generated_at":  datetime.now(timezone.utc),
#         "modified_by":         current_user_id,
#     })

#     return GenerateLinkResponse(
#         token            = token,
#         client_url       = f"{CLIENT_PORTAL_BASE_URL}/{token}",
#         token_expires_at = expires_at,
#     )


# # ===========================================================================
# # INTAKE DATA — save (upsert)
# # ===========================================================================

# async def save_intake_data(
#     db: AsyncSession,
#     session_id: uuid.UUID,
#     payload: IntakeDataSave,
#     current_user_id: uuid.UUID,
#     step_completed: Optional[int] = None,
# ) -> IntakeDataResponse:
#     if payload.has_visa_denial is True and not payload.visa_denial_details:
#         raise HTTPException(
#             status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#             detail="visa_denial_details is required when has_visa_denial is True.",
#         )

#     session = await _get_session_or_404(db, session_id)
#     row     = await _fetch_intake_row(db, session_id)

#     data = payload.model_dump(exclude_unset=True)

#     if "previous_visas" in data and data["previous_visas"] is not None:
#         data["previous_visas"] = _serialize_previous_visas(payload.previous_visas)

#     data["modified_by"] = current_user_id

#     if row:
#         row = await db_update(db, IntakeImmigrationHistory, row.id, data)
#     else:
#         row = IntakeImmigrationHistory(
#             intake_session_id = session_id,
#             created_by        = current_user_id,
#             **{k: v for k, v in data.items() if k != "modified_by"},
#         )
#         row = await db_create(db, row)

#     session_update: dict = {
#         "last_saved_at": datetime.now(timezone.utc),
#         "modified_by":   current_user_id,
#     }
#     if step_completed == 1:
#         session_update["step_1_completed"] = True
#         session_update["current_step"]     = max(session.current_step, 2)
#     elif step_completed == 3:
#         session_update["step_3_completed"] = True
#         session_update["current_step"]     = max(session.current_step, 4)

#     await db_update(db, ClientIntakeSession, session_id, session_update)
#     return _build_intake_data_response(row)


# # ===========================================================================
# # INTAKE DATA — get
# # ===========================================================================

# async def get_intake_data(
#     db: AsyncSession,
#     session_id: uuid.UUID,
# ) -> Optional[IntakeDataResponse]:
#     await _get_session_or_404(db, session_id)
#     row = await _fetch_intake_row(db, session_id)
#     return _build_intake_data_response(row) if row else None


# # ===========================================================================
# # SAVE DRAFT
# # ===========================================================================

# async def save_draft(
#     db: AsyncSession,
#     session_id: uuid.UUID,
#     current_user_id: uuid.UUID,
# ) -> SaveDraftResponse:
#     now     = datetime.now(timezone.utc)
#     updated = await db_update(db, ClientIntakeSession, session_id, {
#         "is_draft":      True,
#         "last_saved_at": now,
#         "modified_by":   current_user_id,
#     })
#     return SaveDraftResponse(
#         detail        = "Draft saved successfully.",
#         last_saved_at = now,
#         current_step  = updated.current_step,
#     )


# # ===========================================================================
# # SUBMIT
# # ===========================================================================

# async def submit_intake(
#     db: AsyncSession,
#     session_id: uuid.UUID,
#     current_user_id: uuid.UUID,
# ) -> SubmitIntakeResponse:
#     session = await _get_session_or_404(db, session_id)

#     if session.is_submitted:
#         raise HTTPException(
#             status_code=status.HTTP_409_CONFLICT,
#             detail="This intake form has already been submitted.",
#         )

#     now = datetime.now(timezone.utc)
#     await db_update(db, ClientIntakeSession, session_id, {
#         "is_submitted": True,
#         "submitted_at": now,
#         "is_draft":     False,
#         "modified_by":  current_user_id,
#     })

#     return SubmitIntakeResponse(
#         detail       = "Intake form submitted successfully.",
#         submitted_at = now,
#         session_id   = session_id,
#     )


# # ===========================================================================
# # CLIENT PROFILE — Screen 26
# # ===========================================================================

# async def get_client_profile(
#     db: AsyncSession,
#     client_id: uuid.UUID,
# ) -> ClientProfileResponse:
#     """
#     GET /clients/{client_id}/profile — Screen 26 aggregated view.

#     Data sources (all from visamodels.py):
#       users                       → name, email, phone, created_at
#       applications                → total_cases, active_cases, active case card
#       deadlines                   → next_deadline_days
#       fees                        → billing_summary (amount_usd is cents)
#       audit_logs                  → recent_activity (last 3)
#       intake_immigration_history  → visa status, nationality, passport details
#     """

#     # ── 1. Load user ──────────────────────────────────────────────────────────
#     user = await db_get_by_id(db, User, client_id)
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Client {client_id} not found.",
#         )

#     first_name = user.first_name or ""
#     last_name  = user.last_name  or ""
#     full_name  = f"{first_name} {last_name}".strip() or user.email
#     initials   = (
#         (first_name[0] if first_name else "") +
#         (last_name[0]  if last_name  else "")
#     ).upper() or "?"

#     # ── 2. Application counts ─────────────────────────────────────────────────
#     total_result = await db.execute(
#         select(func.count(Application.id)).where(Application.user_id == client_id)
#     )
#     total_cases = total_result.scalar_one() or 0

#     active_result = await db.execute(
#         select(func.count(Application.id)).where(
#             Application.user_id == client_id,
#             Application.status.in_(ACTIVE_STATUSES),
#         )
#     )
#     active_cases = active_result.scalar_one() or 0

#     # ── 3. Most recent active application ────────────────────────────────────
#     app_result = await db.execute(
#         select(Application)
#         .where(
#             Application.user_id == client_id,
#             Application.status.in_(ACTIVE_STATUSES),
#         )
#         .order_by(Application.created_at.desc())
#         .limit(1)
#     )
#     active_app = app_result.scalars().first()

#     # ── 4. Active case snapshot ───────────────────────────────────────────────
#     active_case_snapshot: Optional[ActiveCaseSnapshot] = None
#     if active_app:
#         visa_name = None
#         if active_app.visa_type:
#             visa_name = getattr(active_app.visa_type, "name", None) \
#                      or getattr(active_app.visa_type, "code", None)

#         active_case_snapshot = ActiveCaseSnapshot(
#             case_id          = active_app.id,
#             case_number      = active_app.application_number,
#             visa_type_name   = visa_name,
#             status           = active_app.status,
#             progress_percent = active_app.progress_percent,
#             current_stage    = active_app.current_stage,
#             due_date         = active_app.due_date,
#         )

#     # ── 5. Next deadline (from deadlines table) ───────────────────────────────
#     next_deadline_days: Optional[int] = None
#     deadline_result = await db.execute(
#         select(Deadline)
#         .where(
#             Deadline.user_id      == client_id,
#             Deadline.is_completed == False,
#             Deadline.is_dismissed == False,
#         )
#         .order_by(Deadline.due_date.asc())
#         .limit(1)
#     )
#     nearest_deadline = deadline_result.scalars().first()
#     if nearest_deadline:
#         delta = (nearest_deadline.due_date.date() - date.today()).days
#         next_deadline_days = max(delta, 0)

#     # ── 6. Billing summary (fees table, amount_usd in cents) ─────────────────
#     fees_result = await db.execute(
#         select(Fee).where(Fee.user_id == client_id)
#     )
#     all_fees = fees_result.scalars().all()

#     total_billed = sum(f.amount_usd for f in all_fees
#                        if f.status not in ("waived", "cancelled")) / 100
#     total_paid   = sum(f.amount_usd for f in all_fees
#                        if f.status == "paid") / 100
#     outstanding  = round(total_billed - total_paid, 2)

#     # ── 7. Recent activity (last 3 audit_log entries for this user) ───────────
#     activity_result = await db.execute(
#         select(AuditLog)
#         .where(AuditLog.actor_id == client_id)
#         .order_by(AuditLog.created_at.desc())
#         .limit(3)
#     )
#     activity_rows = activity_result.scalars().all()
#     recent_activity = [
#         ActivityItem(
#             action      = row.action,
#             description = row.description,
#             occurred_at = row.created_at,
#         )
#         for row in activity_rows
#     ]

#     # ── 8. Intake data (visa status, nationality, passport) ───────────────────
#     intake_row: Optional[IntakeImmigrationHistory] = None
#     if active_app:
#         session_result = await db.execute(
#             select(ClientIntakeSession).where(
#                 ClientIntakeSession.application_id == active_app.id
#             )
#         )
#         intake_session = session_result.scalars().first()
#         if intake_session:
#             intake_row = await _fetch_intake_row(db, intake_session.id)

#     return ClientProfileResponse(
#         # Hero
#         client_id            = user.id,
#         full_name            = full_name,
#         initials             = initials,
#         email                = user.email,
#         phone                = user.phone,
#         current_visa_status  = getattr(intake_row, "current_visa_status",  None),
#         location             = None,   # V1: skipped
#         employer             = None,   # V1: skipped
#         job_title            = None,   # V1: skipped
#         client_since         = user.created_at,

#         # Contact & Details
#         nationality          = getattr(intake_row, "nationality",          None),
#         passport_number      = getattr(intake_row, "passport_number",      None),
#         passport_expiry_date = getattr(intake_row, "passport_expiry_date", None),

#         # Stats ribbon
#         total_cases          = total_cases,
#         active_cases         = active_cases,
#         unbilled_amount      = outstanding,
#         next_deadline_days   = next_deadline_days,

#         # Overview cards
#         active_case          = active_case_snapshot,
#         billing_summary      = BillingSummarySnapshot(
#             total_billed = total_billed,
#             total_paid   = total_paid,
#             outstanding  = outstanding,
#         ),
#         recent_activity      = recent_activity,
#     )

from sqlalchemy.orm import selectinload


TOKEN_EXPIRY_DAYS      = 7
CLIENT_PORTAL_BASE_URL = f"{settings.FRONTEND_URL}/intake"   # new — was hardcoded to a live production URL

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

async def _load_application_or_404(
    db: AsyncSession, application_id: uuid.UUID
) -> Application:
    """Load Application with proper error handling (400 on bad UUID, 404 on missing)."""
    try:
        application = await db.get(Application, application_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid application_id format: {str(e)}",
        )
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id} not found.",
        )
    return application


def _verify_attorney_owns(application: Application, attorney_id: uuid.UUID) -> None:
    """
    Ensure logged-in attorney is assigned to this application.

    Uses getattr() fallback: if Application.assigned_attorney_id column does not
    exist yet (pre-migration), check is skipped. Once column added, enforced.
    """
    assigned_id = getattr(application, "assigned_attorney_id", None)
    if assigned_id is not None and assigned_id != attorney_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this application.",
        )


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


async def _verify_session_access(
    db: AsyncSession,
    session_id: uuid.UUID,
    attorney_id: uuid.UUID,
) -> ClientIntakeSession:
    """Load session and verify attorney is assigned to the underlying application."""
    session = await _get_session_or_404(db, session_id)
    application = await _load_application_or_404(db, session.application_id)
    _verify_attorney_owns(application, attorney_id)
    return session

# new — lets the EMPLOYEE (client) use the wizard too, not just the attorney
async def _verify_intake_access(
    db: AsyncSession,
    session_id: uuid.UUID,
    current_user_id: uuid.UUID,
) -> ClientIntakeSession:
    """
    Load session and allow access to EITHER:
      - the attorney assigned to the case, OR
      - the employee (client) the case belongs to.
    Used only by the endpoints the client fills out (get/save/submit data).
    Attorney-only actions (accept, request changes, generate link) keep
    using the stricter _verify_session_access above and are unaffected.
    """
    session = await _get_session_or_404(db, session_id)
    application = await _load_application_or_404(db, session.application_id)

    is_the_attorney = getattr(application, "assigned_attorney_id", None) == current_user_id
    is_the_employee = getattr(application, "user_id", None) == current_user_id

    if not is_the_attorney and not is_the_employee:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this intake session.",
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
        phone                = row.phone,            # new
        is_student           = row.is_student,       # new
        company_name         = row.company_name,     # new
        job_title            = row.job_title,         # new
        start_date           = row.start_date,        # new
        annual_salary        = row.annual_salary,     # new
        visa_type_code       = row.visa_type_code,    # new
        passport_number      = row.passport_number,
        passport_expiry_date = row.passport_expiry_date,
        email                = row.email,
        current_visa_status  = row.current_visa_status,
        visa_expiration_date = row.visa_expiration_date,
        has_visa_denial      = row.has_visa_denial,
        visa_denial_details  = row.visa_denial_details,
        has_overstay         = row.has_overstay,
        previous_visas       = _parse_previous_visas(row.previous_visas),
        disclosures_verified_at             = row.disclosures_verified_at,             # new
        disclosures_verified_by_attorney_id = row.disclosures_verified_by_attorney_id, # new
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
        review_status    = session.review_status,
        review_note      = session.review_note,
        reviewed_by      = session.reviewed_by,
        reviewed_at      = session.reviewed_at,
        revision_count   = session.revision_count,
    )


def _intake_status_for(session: Optional[ClientIntakeSession]) -> str:
    """Derive UI status from session state."""
    if session is None:
        return "pending_intake"
    if session.is_submitted:
        return "intake_completed"
    return "intake_in_progress"


# ===========================================================================
# VISA STATUS OPTIONS
# ===========================================================================

def get_visa_status_options() -> VisaStatusOptionsResponse:
    return VisaStatusOptionsResponse(
        items=[VisaStatusOption(value=v, label=l) for v, l in VISA_STATUS_OPTIONS]
    )


# ===========================================================================
# LAWYER APPLICATIONS LIST (NEW)
# ===========================================================================

async def list_assigned_applications(
    db: AsyncSession,
    attorney_id: uuid.UUID,
    status_filter: Optional[str] = None,
) -> List[AssignedApplicationResponse]:
    """
    Returns applications assigned to this attorney + intake session status.

    Filters by assigned_attorney_id IF that column exists on Application.
    Otherwise returns all (logged) and emits a warning — once column is
    added + populated, results will auto-narrow per attorney.
    """
    # Build base query
    # query = select(Application).order_by(Application.created_at.desc())
    query = (
    select(Application)
    .options(selectinload(Application.visa_type))
    .order_by(Application.created_at.desc())
)


    if hasattr(Application, "assigned_attorney_id"):
        query = query.where(Application.assigned_attorney_id == attorney_id)
    # else: returns all apps until column is added (dev-only behavior)
        # query = query.where(Application.case_pipeline_stage.is_(None))   # new — once intake is accepted, case_pipeline_stage is set and it belongs in the main Cases section, not this queue

    result = await db.execute(query)
    applications = result.scalars().all()

    response: List[AssignedApplicationResponse] = []
    for app in applications:
        # Load client
        client = await db_get_by_id(db, User, app.user_id) if app.user_id else None

        # Load session if exists
        session_result = await db.execute(
            select(ClientIntakeSession).where(
                ClientIntakeSession.application_id == app.id
            )
        )
        session = session_result.scalars().first()

        intake_status = _intake_status_for(session)

        # Apply filter
        if status_filter and intake_status != status_filter:
            continue

        # Visa type details (from related VisaType model if attached)
        visa_obj   = getattr(app, "visa_type", None)
        visa_code  = getattr(visa_obj, "code", None) if visa_obj else None
        visa_label = getattr(visa_obj, "name", None) if visa_obj else None

        # Client display
        client_name  = "Unknown"
        client_email = ""
        if client:
            first = client.first_name or ""
            last  = client.last_name  or ""
            client_name  = f"{first} {last}".strip() or (client.email or "Unknown")
            client_email = client.email or ""

        response.append(AssignedApplicationResponse(
            application_id    = app.id,
            client_name       = client_name,
            client_email      = client_email,
            user_id           = app.user_id,
            visa_type         = visa_code,
            visa_type_label   = visa_label,
            status            = intake_status,
            intake_session_id = session.id if session else None,
            intake_step       = session.current_step if session else None,
            assigned_at       = app.created_at,
            hr_reviewed_by    = None,  # TODO: hook up when HR review tracking exists
        ))

    return response


# ===========================================================================
# SESSION — create (with ownership check + 400 on bad UUID)
# ===========================================================================

async def create_session(
    db: AsyncSession,
    payload: IntakeSessionCreate,
    current_user_id: uuid.UUID,
) -> IntakeSessionResponse:
    """
    Create intake session for an application.

    Errors:
      400 — invalid application_id UUID format
      403 — attorney not assigned to this application
      404 — application not found
      409 — intake session already exists for this application
    """
    application = await _load_application_or_404(db, payload.application_id)
    _verify_attorney_owns(application, current_user_id)

    # Check session already exists
    existing = await db.execute(
        select(ClientIntakeSession).where(
            ClientIntakeSession.application_id == payload.application_id
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Intake session already exists for this application.",
        )

    new_session = ClientIntakeSession(
        application_id = payload.application_id,
        current_step   = 1,
        is_draft       = True,
        created_by     = current_user_id,
    )

    if payload.generate_link:
        new_session.token              = secrets.token_urlsafe(32)
        new_session.token_expires_at   = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRY_DAYS)
        new_session.token_generated_by = current_user_id
        new_session.token_generated_at = datetime.now(timezone.utc)

    new_session = await db_create(db, new_session)
    return _build_session_response(new_session)


# ===========================================================================
# SESSION — get by ID (attorney, with ownership)
# ===========================================================================

async def get_session(
    db: AsyncSession,
    session_id: uuid.UUID,
    current_user_id: uuid.UUID,
) -> IntakeSessionResponse:
    session    = await _verify_intake_access(db, session_id, current_user_id)   # new — was _verify_session_access
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired intake link.",
        )
    if session.token_expires_at and session.token_expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This intake link has expired. Ask your attorney to regenerate it.",
        )

    intake_row = await _fetch_intake_row(db, session.id)
    return _build_session_response(session, intake_row)


# ===========================================================================
# GENERATE CLIENT LINK (with ownership)
# ===========================================================================

async def generate_client_link(
    db: AsyncSession,
    session_id: uuid.UUID,
    current_user_id: uuid.UUID,
    note: Optional[str] = None,                                              # NEW
) -> GenerateLinkResponse:
    await _verify_session_access(db, session_id, current_user_id)

    token      = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRY_DAYS)

    await db_update(db, ClientIntakeSession, session_id, {
        "token":              token,
        "token_expires_at":   expires_at,
        "token_generated_by": current_user_id,
        "token_generated_at": datetime.now(timezone.utc),
        "modified_by":        current_user_id,
    })

    # NEW — everything below this line is new, nothing here existed before
    session = await _get_session_or_404(db, session_id)
    application = await _load_application_or_404(db, session.application_id)

    if application.user_id:
        await db_create(db, Notification(
            user_id           = application.user_id,
            notification_type = "case_status_updated",
            category          = "case_update",
            priority           = "high",
            title              = "Your attorney requested your intake details",
            body               = note or "Please complete your intake form so your attorney can move forward with your case.",
            application_id     = application.id,
            actor_id           = current_user_id,
            cta_primary_label = "Complete intake",                          # new
            cta_primary_url   = f"/my-intake/{session_id}",                 # new — use whatever frontend path is confirmed
        ))

        try:
            client_user = await db_get_by_id(db, User, application.user_id)
            attorney    = await db_get_by_id(db, User, current_user_id)
            if client_user and client_user.email:
                attorney_name = f"{attorney.first_name} {attorney.last_name}" if attorney else "Your attorney"
                intake_url    = f"{settings.FRONTEND_URL}/my-intake/{session_id}"   # new — 
                await send_email(
                    to=client_user.email,
                    subject="Your attorney has requested your intake details",
                    body=(
                        f"Hi {client_user.first_name or 'there'},\n\n"
                        f"{attorney_name} has requested that you complete your intake form "
                        f"so they can move forward with your case.\n\n"
                        + (f"Note from your attorney: {note}\n\n" if note else "")
                        + f"Complete it here: {intake_url}\n\n"
                        f"Thanks,\nVyuflo Team"
                    ),
                )
        except Exception as e:
            print(f"[generate_client_link] email failed for session {session_id}: {e}")
    # NEW — end of new code

    return GenerateLinkResponse(
        token            = token,
        client_url       = f"{CLIENT_PORTAL_BASE_URL}/{token}",
        token_expires_at = expires_at,
    )


# ===========================================================================
# INTAKE DATA — save (upsert, with ownership + steps 1-4 progression)
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

    session = await _verify_intake_access(db, session_id, current_user_id)   # new — was _verify_session_access
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

    # Step progression — now handles 1, 2, 3, 4
    if step_completed == 1:
        session_update["step_1_completed"] = True
        session_update["current_step"]     = max(session.current_step, 2)
    elif step_completed == 2:
        session_update["step_2_completed"] = True
        session_update["current_step"]     = max(session.current_step, 3)
    elif step_completed == 3:
        session_update["step_3_completed"] = True
        session_update["current_step"]     = max(session.current_step, 4)
    elif step_completed == 4:
        session_update["step_4_completed"] = True
        session_update["current_step"]     = max(session.current_step, 5)
    # step_completed == 5 handled via submit_intake() not here

    await db_update(db, ClientIntakeSession, session_id, session_update)
    return _build_intake_data_response(row)


# ===========================================================================
# INTAKE DATA — get (with ownership)
# ===========================================================================

async def get_intake_data(
    db: AsyncSession,
    session_id: uuid.UUID,
    current_user_id: uuid.UUID,
) -> Optional[IntakeDataResponse]:
    await _verify_intake_access(db, session_id, current_user_id)   # new — was _verify_session_access
    row = await _fetch_intake_row(db, session_id)
    return _build_intake_data_response(row) if row else None


# ===========================================================================
# SAVE DRAFT (with ownership)
# ===========================================================================

async def save_draft(
    db: AsyncSession,
    session_id: uuid.UUID,
    current_user_id: uuid.UUID,
) -> SaveDraftResponse:
    await _verify_intake_access(db, session_id, current_user_id)   # new — was _verify_session_access
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
# SUBMIT (with ownership + step_5_completed flag)
# ===========================================================================

async def submit_intake(
    db: AsyncSession,
    session_id: uuid.UUID,
    current_user_id: uuid.UUID,
) -> SubmitIntakeResponse:
    session = await _verify_intake_access(db, session_id, current_user_id)   # new — was _verify_session_access
    if session.is_submitted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This intake form has already been submitted.",
        )

    now = datetime.now(timezone.utc)
    await db_update(db, ClientIntakeSession, session_id, {
        "is_submitted":     True,
        "submitted_at":     now,
        "is_draft":         False,
        "review_status":    "pending_review",  # NEW — was never set, stayed "not_submitted" forever
        "step_5_completed": True,    # NEW — mark final step done
        "current_step":     5,       # NEW — pin to last step
        "modified_by":      current_user_id,
    })

    return SubmitIntakeResponse(
        detail       = "Intake form submitted successfully.",
        submitted_at = now,
        session_id   = session_id,
    )
# ===========================================================================
# ATTORNEY REVIEW — accept intake (converts intake → active case)
# ===========================================================================
 
async def accept_intake(
    db: AsyncSession,
    session_id: uuid.UUID,
    payload: AcceptIntakeRequest,
    current_user_id: uuid.UUID,
) -> IntakeReviewDecisionResponse:
    """
    Attorney accepts a submitted intake.
 
    - Requires the session to be submitted and awaiting review
      (review_status == 'pending_review'; also allowed straight from
      'changes_requested' in case the attorney changes their mind before
      the employee resubmits — but NOT already 'accepted', that's a 409).
    - Sets ClientIntakeSession.review_status = 'accepted'.
    - Graduates the Application into an active case:
        intake_accepted_at / intake_accepted_by populated,
        case_pipeline_stage set to 'intake' (first stage of the filing
        pipeline — attorney advances it to 'filed' etc. separately).
    - Notifies the employee.
    """
    session = await _verify_session_access(db, session_id, current_user_id)
 
    if not session.is_submitted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This intake has not been submitted yet — nothing to accept.",
        )
    if session.review_status == "accepted":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This intake has already been accepted.",
        )
 
    now = datetime.now(timezone.utc)
 
    await db_update(db, ClientIntakeSession, session_id, {
        "review_status": "accepted",
        "review_note":   payload.note,
        "reviewed_by":   current_user_id,
        "reviewed_at":   now,
        "modified_by":   current_user_id,
    })
 
    application = await _load_application_or_404(db, session.application_id)
    await db_update(db, Application, application.id, {
        "intake_accepted_at":  now,
        "intake_accepted_by":  current_user_id,
        "case_pipeline_stage": "intake",
        "modified_by":         current_user_id,
    })
 
    if application.user_id:
        await db_create(db, Notification (
            user_id =     application.user_id,
            notification_type = "case_status_updated",
            category =         "case_update",
            priority =          "medium",
            title =             "Your intake was accepted",
            body =               "Your attorney has accepted your intake. Your case is now active and moving into the filing pipeline.",
            application_id =    application.id,
            actor_id =           current_user_id,
            cta_primary_label = "View case",             # new — see next fix, why this matters
            cta_primary_url   = f"/applications/{application.id}",   # new
        ))
 
    return IntakeReviewDecisionResponse(
        detail               = "Intake accepted. Application has been converted into an active case.",
        session_id           = session_id,
        application_id       = application.id,
        review_status        = "accepted",
        reviewed_at           = now,
        revision_count        = session.revision_count,
        intake_accepted_at    = now,
        case_pipeline_stage   = "intake",
    )
 
 
# ===========================================================================
# ATTORNEY REVIEW — mark background disclosures as verified (Immigration step)
# ===========================================================================

async def verify_disclosures(
    db: AsyncSession,
    session_id: uuid.UUID,
    current_user_id: uuid.UUID,
) -> VerifyDisclosuresResponse:
    """
    Attorney confirms they've reviewed the client's background disclosures
    (visa denial / overstay / previous visas) on the Immigration History step.

    Attorney-only — uses _verify_session_access, not _verify_intake_access,
    so the employee can never mark their own disclosures as verified.

    Requires an IntakeImmigrationHistory row to already exist (i.e. the
    client must have filled in Step 3 before this can be verified) — 404
    if nothing's been saved for this session yet.
    """
    await _verify_session_access(db, session_id, current_user_id)

    row = await _fetch_intake_row(db, session_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No immigration history has been saved for this session yet — nothing to verify.",
        )

    now = datetime.now(timezone.utc)
    await db_update(db, IntakeImmigrationHistory, row.id, {
        "disclosures_verified_by_attorney_id": current_user_id,
        "disclosures_verified_at":             now,
        "modified_by":                         current_user_id,
    })

    return VerifyDisclosuresResponse(
        detail                              = "Disclosures marked as verified.",
        session_id                          = session_id,
        disclosures_verified_at             = now,
        disclosures_verified_by_attorney_id = current_user_id,
    )


# ===========================================================================
# ATTORNEY REVIEW — request changes (sends the whole form back)
# ===========================================================================
 
async def request_intake_changes(
    db: AsyncSession,
    session_id: uuid.UUID,
    payload: RequestIntakeChangesRequest,
    current_user_id: uuid.UUID,
) -> IntakeReviewDecisionResponse:
    """
    Attorney sends the intake back for corrections — whole-form, per the
    agreed design (no per-step/per-field granularity in V1).
 
    Reopens the ENTIRE wizard: is_submitted/is_draft reset, all step
    completion flags cleared, current_step pinned back to 1. The employee
    sees correction_note as the reason and redoes the form from the start.
    revision_count increments so the attorney can see "this is resubmission #2".
    """
    session = await _verify_session_access(db, session_id, current_user_id)
 
    if not session.is_submitted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This intake has not been submitted yet — nothing to send back.",
        )
    if session.review_status == "accepted":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This intake was already accepted and converted into a case; it can no longer be sent back.",
        )
 
    now = datetime.now(timezone.utc)
 
    await db_update(db, ClientIntakeSession, session_id, {
        "review_status":    "changes_requested",
        "review_note":      payload.correction_note,
        "reviewed_by":       current_user_id,
        "reviewed_at":       now,
        "revision_count":    session.revision_count + 1,
        # Whole-form reopen — employee redoes everything from step 1.
        "is_submitted":      False,
        "submitted_at":      None,
        "is_draft":          True,
        "current_step":      1,
        "step_1_completed":  False,
        "step_2_completed":  False,
        "step_3_completed":  False,
        "step_4_completed":  False,
        "step_5_completed":  False,
        "modified_by":       current_user_id,
    })
 
    application = await _load_application_or_404(db, session.application_id)
    if application.user_id:
        await db_create(db, Notification (
            user_id =           application.user_id,
            notification_type = "case_status_updated",
            category =          "case_update",
            priority =           "high",
            title =            "Your intake needs corrections",
            body =               payload.correction_note,
            application_id =     application.id,
            actor_id =          current_user_id,
            cta_primary_label = "Complete intake",                # new
            cta_primary_url   = f"/my-intake/{session.id}",       # new
        ))
                # NEW — sends an email to the employee, in addition to the notification above
        try:
            client_user = await db_get_by_id(db, User, application.user_id)
            attorney    = await db_get_by_id(db, User, current_user_id)
            if client_user and client_user.email:
                attorney_name = f"{attorney.first_name} {attorney.last_name}" if attorney else "Your attorney"
                intake_url    = f"{settings.FRONTEND_URL}/my-intake/{session_id}"   # new
                await send_email(
                    to=client_user.email,
                    subject="Your intake needs corrections",
                    body=(
                        f"Hi {client_user.first_name or 'there'},\n\n"
                        f"{attorney_name} has reviewed your intake and requested corrections:\n\n"
                        f"{payload.correction_note}\n\n"
                        f"Update it here: {intake_url}\n\n"
                        f"Thanks,\nVyuflo Team"
                    ),
                )
        except Exception as e:
            print(f"[request_intake_changes] email failed for session {session.id}: {e}")
 
    return IntakeReviewDecisionResponse(
        detail          = "Changes requested. The employee has been notified and the form has been reopened.",
        session_id      = session_id,
        application_id  = application.id,
        review_status   = "changes_requested",
        reviewed_at      = now,
        revision_count   = session.revision_count + 1,
    )


# ===========================================================================
# CLIENT PROFILE — Screen 26 (safer date handling)
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
            receipt_number   = active_app.receipt_number,   # NEW
            priority_date    = active_app.priority_date,     # NEW
        )

    # ── 5. Next deadline (handles both datetime and date types) ───────────────
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
    if nearest_deadline and nearest_deadline.due_date:
        # Handle both datetime and date types defensively
        due = nearest_deadline.due_date
        if isinstance(due, datetime):
            due = due.date()
        delta = (due - date.today()).days
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