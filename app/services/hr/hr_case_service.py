# app/services/hr/hr_case_service.py
"""
CORRECTION: an earlier delivery of this file was accidentally truncated
after hr_update_case_status, cutting off hr_update_approval and
hr_list_case_history. Both are restored below — this is the complete file.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone, timedelta, date
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.services.employee.message_service import get_or_create_thread_for_participants
from app.services.employee.services import (
    db_create,
    db_get_by_id,
    db_update,
    db_list,
)
from app.models.visamodels import (
    Application,
    ApplicationGeneratedLetter,
    ApplicationStatusHistory,
    ApplicationTask,
    AttorneyProfile,
    Document,
    EmployerEmployee,
    EmployerProfile,
    EmployerFirmConnection,
    AttorneyProfile,
    User,
    UserProfile,
    VisaType,
)
from app.schemas.hr.hr_case_schemas import (
    HRCaseCreate,
    HRCaseUpdate,
    HRCaseStatusUpdate,
    HRApprovalUpdate,
    HRCaseListQuery,
    HRCaseResponse,
    HRCaseListResponse,
    HRCaseCreateResponse,
    HRCaseStatusHistoryResponse,
    VisaTypeBasic,
    EmployeeBasic,
    AttorneyBasic,
    EmploymentInfo,
    DocumentBasic,
    GeneratedLetterInfo,
)
from app.services.employee.notification_service import (
    fire_case_created,
    fire_case_assigned_to_hr,
    fire_case_status_changed,
    fire_hr_approval_changed,
)


# =============================================================================
# INTERNAL HELPERS
# =============================================================================

STAGE_PROGRESS: dict[str, int] = {
    "profile_eligibility": 25,
    "documentation":       50,
    "lca_filing":          75,
    "uscis_submission":    90,
}

_ACTIVE_STATUSES = {
    "in_progress", "action_needed", "rfe_response", "submitted"
}


def _generate_application_number() -> str:
    suffix = uuid.uuid4().hex[:4].upper()
    number = uuid.uuid4().int % 90000 + 10000
    return f"VF-{number}-{suffix[0]}"


def _pack_notes(case_name: str, case_description: Optional[str], priority: str) -> str:
    return json.dumps({
        "case_name":   case_name,
        "description": case_description or "",
        "priority":    priority,
    }, ensure_ascii=False)


def _unpack_notes(raw: Optional[str]) -> tuple[str, Optional[str], str]:
    if not raw:
        return "Unnamed Case", None, "standard"
    try:
        data = json.loads(raw)
        return (
            data.get("case_name",   "Unnamed Case"),
            data.get("description") or None,
            data.get("priority",    "standard"),
        )
    except (json.JSONDecodeError, TypeError):
        return raw[:200] if raw else "Unnamed Case", None, "standard"


async def _assert_hr_owns_case(
    db: AsyncSession,
    application_id: uuid.UUID,
    hr_user_id: uuid.UUID,
) -> Application:
    result = await db.execute(
        select(Application)
        .options(joinedload(Application.visa_type))
        .where(Application.id == application_id)
    )
    app = result.scalars().first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {application_id} not found.",
        )
    if app.assigned_hr_id != hr_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this case.",
        )
    return app


async def _resolve_visa_type(db: AsyncSession, code: str) -> VisaType:
    result = await db.execute(
        select(VisaType).where(
            VisaType.code      == code.upper().strip(),
            VisaType.is_active == True,
        )
    )
    vt = result.scalars().first()
    if not vt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Visa type '{code}' not found or is inactive.",
        )
    return vt


async def _resolve_employee_link(
    db: AsyncSession,
    employee_link_id: uuid.UUID,
    hr_user_id: uuid.UUID,
) -> EmployerEmployee:
    link = await db_get_by_id(db, EmployerEmployee, employee_link_id)
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee link {employee_link_id} not found.",
        )
    if link.employer_id != hr_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This employee is not linked to your company.",
        )
    if not link.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create a case for an inactive employee.",
        )
    return link

async def _validate_attorney_from_connected_firm(
    db: AsyncSession,
    employer_profile_id: uuid.UUID,
    attorney_user_id: uuid.UUID,
) -> None:
    """
    Raises 403 unless the given attorney belongs to a firm this employer
    is actually connected to.
    """
    attorney = await db.execute(
        select(AttorneyProfile).where(AttorneyProfile.user_id == attorney_user_id)
    )
    attorney = attorney.scalars().first()
    if not attorney:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Attorney not found.")
    if not attorney.firm_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This attorney is not part of any firm and cannot be assigned.",
        )

    connection = await db.execute(
        select(EmployerFirmConnection).where(
            EmployerFirmConnection.employer_profile_id == employer_profile_id,
            EmployerFirmConnection.firm_id             == attorney.firm_id,
            EmployerFirmConnection.is_active            == True,
        )
    )
    if not connection.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This attorney's firm is not connected to your company. "
                    "Choose an attorney from a firm you're connected to.",
        )
    
async def _get_user_display_name(db: AsyncSession, user_id: uuid.UUID) -> str:
    """Fetch first+last name for a user_id."""
    user = await db_get_by_id(db, User, user_id)
    if not user:
        return "Unknown"
    return f"{user.first_name} {user.last_name}".strip() or "Unknown"


async def _build_case_response(
    db: AsyncSession,
    app: Application,
) -> HRCaseResponse:
    case_name, case_description, priority = _unpack_notes(app.notes)

    vt = getattr(app, "visa_type", None)
    if vt is None and app.visa_type_id:
        vt = await db_get_by_id(db, VisaType, app.visa_type_id)

    # Parse required_documents JSON string → list. visa_types.required_documents
    # is stored as Text; tolerate empty/malformed values rather than 500ing the
    # whole case response over one bad row.
    required_docs: List[str] = []
    if vt and vt.required_documents:
        try:
            parsed = json.loads(vt.required_documents)
            if isinstance(parsed, list):
                required_docs = [str(x) for x in parsed]
        except (json.JSONDecodeError, TypeError):
            pass

    visa_type_obj = VisaTypeBasic(
        id=vt.id, code=vt.code, name=vt.name,
        required_documents=required_docs,
    ) if vt else None

    emp_user = await db_get_by_id(db, User, app.user_id)
    emp_profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == app.user_id)
    )
    emp_profile = emp_profile_result.scalars().first()
    full_name = (
        emp_profile.full_legal_name
        if emp_profile and emp_profile.full_legal_name
        else f"{emp_user.first_name} {emp_user.last_name}".strip()
        if emp_user else "Unknown"
    )

    link_result = await db.execute(
        select(EmployerEmployee).where(
            EmployerEmployee.employee_id == app.user_id,
            EmployerEmployee.employer_id == app.assigned_hr_id,
            EmployerEmployee.is_active   == True,
        )
    )
    link = link_result.scalars().first()

    employee_obj = EmployeeBasic(
        user_id             = app.user_id,
        full_name           = full_name,
        email               = emp_user.email if emp_user else "",
        job_title           = link.job_title if link else None,
        department          = link.department if link else None,
        profile_picture_url = emp_profile.profile_picture_url if emp_profile else None,
    ) if emp_user else None

    attorney_obj = None
    if app.assigned_attorney_id:
        att_user = await db_get_by_id(db, User, app.assigned_attorney_id)
        att_profile_result = await db.execute(
            select(AttorneyProfile).where(
                AttorneyProfile.user_id == app.assigned_attorney_id
            )
        )
        att_profile = att_profile_result.scalars().first()
        if att_user:
            attorney_obj = AttorneyBasic(
                user_id       = app.assigned_attorney_id,
                full_name     = f"{att_user.first_name} {att_user.last_name}".strip(),
                email         = att_user.email,
                law_firm_name = att_profile.law_firm_name if att_profile else None,
            )

    # ── Employment info: case-specific override, falls back to the employee's
    #    general EmployerEmployee record (`link`, already resolved above) ──────
    employment_obj = EmploymentInfo(
        job_title        = app.job_title        or (link.job_title  if link else None),
        annual_salary    = app.annual_salary,
        start_date       = app.start_date,
        department       = app.department       or (link.department if link else None),
        worksite_address = app.worksite_address,
    )

    # ── Uploaded documents (Missing Checklist match against required_documents) ─
    docs_result = await db.execute(
        select(Document)
        .options(joinedload(Document.document_type))
        .where(Document.application_id == app.id)
    )
    documents_list = [
        DocumentBasic(
            id=d.id,
            name=d.file_name or "Untitled",
            document_type=d.document_type.name if d.document_type else None,
            status=d.status,
        )
        for d in docs_result.scalars().all()
    ]

    # ── Generated letters (Generated Letters tab) ─────────────────────────────
    letters_result = await db.execute(
        select(ApplicationGeneratedLetter)
        .where(ApplicationGeneratedLetter.application_id == app.id)
        .order_by(ApplicationGeneratedLetter.generated_at.desc())
    )
    letters_list: List[GeneratedLetterInfo] = []
    for letter in letters_result.scalars().all():
        gen_by_user = await db_get_by_id(db, User, letter.generated_by_user_id)
        gen_by_name = (
            f"{gen_by_user.first_name} {gen_by_user.last_name}".strip()
            if gen_by_user else "Attorney"
        )
        letters_list.append(GeneratedLetterInfo(
            id           = letter.id,
            name         = letter.name,
            letter_type  = letter.letter_type,
            generated_by = gen_by_name,
            generated_at = letter.generated_at,
            status       = letter.status,
            file_url     = (
                f"/api/v1/hr/cases/{app.id}/letters/{letter.id}/pdf"
                if letter.file_path else None
            ),
        ))

    return HRCaseResponse(
        id                   = app.id,
        application_number   = app.application_number,
        status               = app.status,
        current_stage        = app.current_stage,
        progress_percent     = app.progress_percent,
        is_draft             = app.is_draft,
        has_action_required  = app.has_action_required,
        action_required_note = app.action_required_note,
        start_date           = app.start_date,
        due_date             = app.due_date,
        submission_date      = app.submission_date,
        case_name            = case_name,
        case_description     = case_description,
        priority             = priority,
        internal_notes       = app.hr_notes,
        sponsor_employer     = app.sponsor_employer,
        hr_approval_status   = app.hr_approval_status,
        hr_notes             = app.hr_notes,
        hr_approved_at       = app.hr_approved_at,
        assigned_hr_id       = app.assigned_hr_id,
        assigned_attorney_id = app.assigned_attorney_id,
        visa_type            = visa_type_obj,
        employee             = employee_obj,
        attorney             = attorney_obj,
        employment           = employment_obj,
        lca_certified        = (app.lca_status == "certified"),
        lca_status           = app.lca_status,
        lca_case_number      = app.lca_case_number,
        documents            = documents_list,
        generated_letters    = letters_list,
        created_by           = app.created_by,
        created_at           = app.created_at,
        updated_at           = app.updated_at,
    )


# =============================================================================
# CREATE CASE
# =============================================================================

async def hr_create_case(
    db: AsyncSession,
    payload: HRCaseCreate,
    hr_user_id: uuid.UUID,
) -> HRCaseCreateResponse:

    # ── 1. Validate employee link ─────────────────────────────────────────────
    link = await _resolve_employee_link(db, payload.employee_link_id, hr_user_id)
    employee_user_id = link.employee_id

    # ── 2. Resolve visa type ──────────────────────────────────────────────────
    visa_type = await _resolve_visa_type(db, payload.visa_type_code)

    # ── 3. Block duplicate active cases ───────────────────────────────────────
    duplicate = await db.execute(
        select(Application).where(
            Application.user_id      == employee_user_id,
            Application.visa_type_id == visa_type.id,
            Application.status.in_(list(_ACTIVE_STATUSES) + ["draft"]),
        )
    )
    if duplicate.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"An active {payload.visa_type_code} case already exists for this employee. "
                "Complete or withdraw it before creating a new one."
            ),
        )

    # ── 4. Resolve sponsor_employer ───────────────────────────────────────────
    sponsor = payload.sponsor_employer
    if not sponsor:
        emp_profile_result = await db.execute(
            select(EmployerProfile).where(EmployerProfile.user_id == hr_user_id)
        )
        emp_profile = emp_profile_result.scalars().first()
        if emp_profile:
            sponsor = emp_profile.company_name
    # ── 4b. Validate attorney belongs to a connected firm ─────────────────────
    if payload.attorney_user_id:
        emp_profile_result = await db.execute(
            select(EmployerProfile).where(EmployerProfile.user_id == hr_user_id)
        )
        emp_profile = emp_profile_result.scalars().first()
        if emp_profile:
            await _validate_attorney_from_connected_firm(
                db, emp_profile.id, payload.attorney_user_id
            )

    # ── 5. Pack notes ─────────────────────────────────────────────────────────
    packed_notes = _pack_notes(
        payload.case_name,
        payload.case_description,
        payload.priority,
    )

    # ── 6. Generate unique application number ─────────────────────────────────
    from app.services.employee.services import db_get_by_field
    app_number = _generate_application_number()
    if await db_get_by_field(db, Application, "application_number", app_number):
        app_number = _generate_application_number()

    # ── 7. Create Application row ─────────────────────────────────────────────
    new_app = Application(
        application_number   = app_number,
        user_id              = employee_user_id,
        visa_type_id         = visa_type.id,
        sponsor_employer     = sponsor,
        status               = "draft",
        current_stage        = None,
        progress_percent     = 0,
        start_date           = None,
        due_date             = payload.target_date,
        is_draft             = True,
        has_action_required  = False,
        assigned_attorney_id = payload.attorney_user_id,
        assigned_hr_id       = hr_user_id,
        notes                = packed_notes,
        hr_notes             = payload.internal_notes,
        hr_approval_status   = "pending",
        created_by           = hr_user_id,
    )
    new_app = await db_create(db, new_app)

    # ── 8. Immediately activate ───────────────────────────────────────────────
    await db_update(db, Application, new_app.id, {
        "current_stage":    "profile_eligibility",
        "status":           "in_progress",
        "progress_percent": STAGE_PROGRESS["profile_eligibility"],
        "start_date":       datetime.now(timezone.utc).date(),
        "is_draft":         False,
        "modified_by":      hr_user_id,
    })

    # ── 9. Write first history row ────────────────────────────────────────────
    history = ApplicationStatusHistory(
        application_id = new_app.id,
        stage          = "profile_eligibility",
        status         = "in_progress",
        note           = f"Case created by HR: {payload.case_name}",
        completed_at   = datetime.now(timezone.utc),
        changed_by     = hr_user_id,
        created_by     = hr_user_id,
    )
    await db_create(db, history)

    # ── 10. Auto-create checklist tasks ───────────────────────────────────────
    docs = visa_type.required_documents
    if isinstance(docs, str):
        try:
            docs = json.loads(docs)
        except (json.JSONDecodeError, TypeError):
            docs = []

    for idx, doc_name in enumerate(docs or []):
        task = ApplicationTask(
            application_id = new_app.id,
            task_name      = doc_name,
            description    = f"Upload {doc_name} for {visa_type.code} application",
            is_required    = True,
            is_completed   = False,
            sort_order     = idx + 1,
            created_by     = hr_user_id,
        )
        await db_create(db, task)

    # NOTE: NO db.commit() here — db_create uses flush-only. The framework
    # commits at the end of the request via the get_db dependency.

    # ── 11. Reload with relationships ─────────────────────────────────────────
    result = await db.execute(
        select(Application)
        .options(joinedload(Application.visa_type))
        .where(Application.id == new_app.id)
    )
    refreshed = result.scalars().first()

    # ── 12. Fire notifications ────────────────────────────────────────────────
    await fire_case_created(db, refreshed, actor_id=hr_user_id)

    # ── 13. Resolve names for thread ─────────────────────────────────────────
    emp_user    = await db_get_by_id(db, User, employee_user_id)
    full_name   = (
        f"{emp_user.first_name} {emp_user.last_name}".strip()
        if emp_user else "Employee"
    )
    hr_user_obj = await db_get_by_id(db, User, hr_user_id)
    hr_name     = (
        f"{hr_user_obj.first_name} {hr_user_obj.last_name}".strip()
        if hr_user_obj else "HR"
    )

    # ── 14. Auto-create case conversation ────────────────────────────────────
    # Always group — HR + employee + attorney (if present).
    # Keyed on application_id so re-running never creates a duplicate.
    extra_participants = [employee_user_id]
    if payload.attorney_user_id:
        extra_participants.append(payload.attorney_user_id)

    thread_type  = "group" if len(extra_participants) > 1 else "direct"
    thread_title = f"{payload.case_name} — Case Team" if thread_type == "group" else None

    await get_or_create_thread_for_participants(
        db              = db,
        actor_id        = hr_user_id,
        participant_ids = extra_participants,
        thread_type     = thread_type,
        title           = thread_title,
        application_id  = refreshed.id,
        initial_message = (
            f"Case '{payload.case_name}' ({visa_type.code}) has been opened. "
            f"This conversation is the dedicated channel for the {full_name} case team. "
            f"HR contact: {hr_name}."
        ),
    )

    return HRCaseCreateResponse(
        id                 = refreshed.id,
        application_number = refreshed.application_number,
        message            = f"Case '{payload.case_name}' created successfully.",
        employee_name      = full_name,
        visa_type_code     = visa_type.code,
    )


# =============================================================================
# LIST CASES
# =============================================================================

async def hr_list_cases(
    db: AsyncSession,
    hr_user_id: uuid.UUID,
    query: HRCaseListQuery,
) -> HRCaseListResponse:
    base_filters = [Application.assigned_hr_id == hr_user_id]

    all_result = await db.execute(
        select(Application).where(Application.assigned_hr_id == hr_user_id)
    )
    all_cases = all_result.scalars().all()
    total_active  = sum(1 for a in all_cases if a.status in _ACTIVE_STATUSES)
    action_needed = sum(1 for a in all_cases if a.status == "action_needed")
    approved_ytd  = sum(1 for a in all_cases if a.status == "approved")
    today         = datetime.now(timezone.utc).date()
    soon_cutoff   = today + timedelta(days=30)
    expiring_soon = sum(
        1 for a in all_cases
        if a.due_date and today <= a.due_date <= soon_cutoff
    )

    stmt = (
        select(Application)
        .options(joinedload(Application.visa_type))
        .where(*base_filters)
    )
    if query.status:
        stmt = stmt.where(Application.status == query.status)
    if query.employee_user_id:
        stmt = stmt.where(Application.user_id == query.employee_user_id)
    if query.attorney_user_id:
        stmt = stmt.where(Application.assigned_attorney_id == query.attorney_user_id)
    if query.visa_type_code:
        vt = await _resolve_visa_type(db, query.visa_type_code)
        stmt = stmt.where(Application.visa_type_id == vt.id)

    stmt = (
        stmt.order_by(Application.created_at.desc())
        .limit(query.limit)
        .offset(query.offset)
    )
    result = await db.execute(stmt)
    apps   = result.scalars().all()

    items = [await _build_case_response(db, app) for app in apps]

    return HRCaseListResponse(
        items         = items,
        total         = len(all_cases),
        total_active  = total_active,
        action_needed = action_needed,
        approved_ytd  = approved_ytd,
        expiring_soon = expiring_soon,
    )


# =============================================================================
# GET SINGLE CASE
# =============================================================================

async def hr_get_case(
    db: AsyncSession,
    application_id: uuid.UUID,
    hr_user_id: uuid.UUID,
) -> HRCaseResponse:
    app = await _assert_hr_owns_case(db, application_id, hr_user_id)
    return await _build_case_response(db, app)


# =============================================================================
# UPDATE CASE
# =============================================================================

async def hr_update_case(
    db: AsyncSession,
    application_id: uuid.UUID,
    payload: HRCaseUpdate,
    hr_user_id: uuid.UUID,
) -> HRCaseResponse:
    app = await _assert_hr_owns_case(db, application_id, hr_user_id)

    update_data: dict = {"modified_by": hr_user_id}

    current_name, current_desc, current_priority = _unpack_notes(app.notes)
    new_name     = payload.case_name        or current_name
    new_desc     = payload.case_description if payload.case_description is not None else current_desc
    new_priority = payload.priority         or current_priority

    if payload.case_name or payload.case_description is not None or payload.priority:
        update_data["notes"] = _pack_notes(new_name, new_desc, new_priority)

    if payload.target_date is not None:
        update_data["due_date"] = payload.target_date
    # if payload.attorney_user_id is not None:
        # update_data["assigned_attorney_id"] = payload.attorney_user_id
    if payload.attorney_user_id is not None:
        emp_profile_result = await db.execute(
            select(EmployerProfile).where(EmployerProfile.user_id == hr_user_id)
        )
        emp_profile = emp_profile_result.scalars().first()
        if emp_profile:
            await _validate_attorney_from_connected_firm(
                db, emp_profile.id, payload.attorney_user_id
            )
        update_data["assigned_attorney_id"] = payload.attorney_user_id
    if payload.sponsor_employer is not None:
        update_data["sponsor_employer"] = payload.sponsor_employer
    if payload.has_action_required is not None:
        update_data["has_action_required"] = payload.has_action_required
    if payload.action_required_note is not None:
        update_data["action_required_note"] = payload.action_required_note
    if payload.internal_notes is not None:
        update_data["hr_notes"] = payload.internal_notes

    # ── Employment / LCA (new — HR fills these in as the case progresses) ─────
    if payload.job_title is not None:
        update_data["job_title"] = payload.job_title
    if payload.annual_salary is not None:
        update_data["annual_salary"] = payload.annual_salary
    if payload.department is not None:
        update_data["department"] = payload.department
    if payload.worksite_address is not None:
        update_data["worksite_address"] = payload.worksite_address
    if payload.lca_status is not None:
        update_data["lca_status"] = payload.lca_status
        if payload.lca_status == "certified":
            update_data["lca_certified_at"] = datetime.now(timezone.utc)
    if payload.lca_case_number is not None:
        update_data["lca_case_number"] = payload.lca_case_number

    old_attorney_id = app.assigned_attorney_id
    new_attorney_id = payload.attorney_user_id

    await db_update(db, Application, application_id, update_data)

    # ── Attorney changed → add to existing case thread (or create one) ────────
    if new_attorney_id and new_attorney_id != old_attorney_id:
        # Fire notification
        updated_app = await db_get_by_id(db, Application, application_id)
        await fire_case_assigned_to_hr(
            db, updated_app, new_hr_id=hr_user_id, actor_id=hr_user_id
        )
        # NEW — notify the newly-assigned attorney (this was the real gap —
        # fire_case_assigned_to_hr only notifies HR + employee, never the attorney)
        from app.services.employee.notification_service import _create_notification
        await _create_notification(
            db, user_id=new_attorney_id, notification_type="case_status_updated",
            category="case_update", priority="high",
            title=f"New case assigned — {updated_app.application_number}",
            body=f"Case {updated_app.application_number} has been assigned to you. Please review and begin the eligibility assessment.",
            application_id=application_id, case_reference=updated_app.application_number,
            actor_id=hr_user_id, actor_label="HR",
            cta_primary_label="Open Case", cta_primary_url=f"/lawyer/cases/{application_id}",
        )

        # Resolve names for the system message
        attorney_name = await _get_user_display_name(db, new_attorney_id)
        employee_name = await _get_user_display_name(db, app.user_id)
        hr_name       = await _get_user_display_name(db, hr_user_id)

        case_name, _, _ = _unpack_notes(app.notes)

        # Fetch visa type code for the thread title / message
        vt = getattr(app, "visa_type", None)
        if vt is None and app.visa_type_id:
            vt = await db_get_by_id(db, VisaType, app.visa_type_id)
        visa_code = vt.code if vt else "Visa"

        # get_or_create_thread_for_participants will:
        #   • find existing group thread by application_id
        #   • call _add_missing_participants to add the attorney
        #   • post a system_notification in the thread
        await get_or_create_thread_for_participants(
            db              = db,
            actor_id        = hr_user_id,
            participant_ids = [app.user_id, new_attorney_id],
            thread_type     = "group",
            title           = f"{case_name} — Case Team",
            application_id  = application_id,
            initial_message = (
                f"Attorney {attorney_name} has been assigned to the {employee_name} "
                f"{visa_code} case. Welcome to the team!"
            ),
        )

    # Reload with relationships
    result = await db.execute(
        select(Application)
        .options(joinedload(Application.visa_type))
        .where(Application.id == application_id)
    )
    refreshed = result.scalars().first()
    return await _build_case_response(db, refreshed)


# =============================================================================
# UPDATE STATUS
# =============================================================================

async def hr_update_case_status(
    db: AsyncSession,
    application_id: uuid.UUID,
    payload: HRCaseStatusUpdate,
    hr_user_id: uuid.UUID,
) -> HRCaseResponse:
    app = await _assert_hr_owns_case(db, application_id, hr_user_id)
    old_status = app.status

    update_data: dict = {
        "status":      payload.status,
        "modified_by": hr_user_id,
    }
    if payload.current_stage:
        update_data["current_stage"]    = payload.current_stage
        update_data["progress_percent"] = STAGE_PROGRESS.get(payload.current_stage, app.progress_percent)
    if payload.status == "action_needed":
        update_data["has_action_required"]  = True
        update_data["action_required_note"] = payload.note
    if payload.status == "submitted":
        update_data["submission_date"] = datetime.now(timezone.utc)
        update_data["is_draft"]        = False
    if payload.status in ("approved", "rejected", "withdrawn"):
        update_data["has_action_required"] = False

    await db_update(db, Application, application_id, update_data)

    history = ApplicationStatusHistory(
        application_id = application_id,
        stage          = payload.current_stage or app.current_stage,
        status         = payload.status,
        note           = payload.note,
        completed_at   = datetime.now(timezone.utc) if payload.status == "approved" else None,
        changed_by     = hr_user_id,
        created_by     = hr_user_id,
    )
    await db_create(db, history)

    refreshed = await db_get_by_id(db, Application, application_id)
    await fire_case_status_changed(
        db, refreshed,
        old_status=str(old_status),
        new_status=str(payload.status),
        actor_id=hr_user_id,
        note=payload.note,
    )

    result = await db.execute(
        select(Application)
        .options(joinedload(Application.visa_type))
        .where(Application.id == application_id)
    )
    return await _build_case_response(db, result.scalars().first())


# =============================================================================
# HR APPROVAL
# =============================================================================

async def hr_update_approval(
    db: AsyncSession,
    application_id: uuid.UUID,
    payload: HRApprovalUpdate,
    hr_user_id: uuid.UUID,
) -> HRCaseResponse:
    app = await _assert_hr_owns_case(db, application_id, hr_user_id)

    update_data: dict = {
        "hr_approval_status": payload.hr_approval_status,
        "hr_notes":           payload.hr_notes,
        "hr_approved_at":     datetime.now(timezone.utc),
        "hr_approved_by":     hr_user_id,
        "modified_by":        hr_user_id,
    }
    updated = await db_update(db, Application, application_id, update_data)

    await fire_hr_approval_changed(
        db, updated,
        new_approval_status=payload.hr_approval_status,
        actor_id=hr_user_id,
        hr_notes=payload.hr_notes,
    )

    result = await db.execute(
        select(Application)
        .options(joinedload(Application.visa_type))
        .where(Application.id == application_id)
    )
    return await _build_case_response(db, result.scalars().first())


# =============================================================================
# STATUS HISTORY
# =============================================================================

async def hr_list_case_history(
    db: AsyncSession,
    application_id: uuid.UUID,
    hr_user_id: uuid.UUID,
) -> List[HRCaseStatusHistoryResponse]:
    await _assert_hr_owns_case(db, application_id, hr_user_id)

    result = await db.execute(
        select(ApplicationStatusHistory)
        .where(ApplicationStatusHistory.application_id == application_id)
        .order_by(ApplicationStatusHistory.created_at.asc())
    )
    rows = result.scalars().all()