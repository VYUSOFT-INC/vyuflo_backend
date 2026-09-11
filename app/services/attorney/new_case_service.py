from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.email import send_email

from app.models.visamodels import (
    ApplicationTask,
    User,
    Application,
    ApplicationStatusHistory,
    ApplicationFiling,
    VisaType,
    AttorneyProfile,
    ConsultationBooking,
    ConsultationSlot,
    Notification,
)
from app.schemas.attorney.new_case_schemas import (
    AttorneyTaskListResponse,
    AttorneyTaskResponse,
    CompleteAttorneyTaskRequest,
    NewCaseCreateRequest,
    NewCaseCreateResponse,
    ConsultedClientOut,
    FileCaseRequest,
    FileCaseResponse,
    RecordFilingRequest,
    FilingResponse,
    FilingListResponse,
    AttorneyTaskCreateRequest,
)
from app.services.employee.services import db_create, db_get_by_id

# ── Shared HR-relay state machine — single source of truth, also imported
#    by hr_task_service.py and application_services.py.
from app.services.employee.task_relay import unpack_task_description


async def create_lawyer_case(
    db: AsyncSession,
    data: NewCaseCreateRequest,
    attorney_user_id: uuid.UUID,
) -> NewCaseCreateResponse:
    # ── 1. Validate client exists ────────────────────────────────────────
    client = await db_get_by_id(db, User, data.client_user_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail="Client not found.")

    # ── 2. Resolve visa type code → id ───────────────────────────────────
    visa_type = await db.scalar(select(VisaType).where(VisaType.code == data.visa_type_code))
    if not visa_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                             detail=f"Visa type '{data.visa_type_code}' not found.")

    # ── 3. Create the case ────────────────────────────────────────────────
    # NOTE: `applications` has no dedicated case_name or priority column.
    # case_name is returned to the frontend but not stored as its own field;
    # priority is folded into `notes` for now. Add real columns later if you
    # need to filter/sort by either one.
    application = Application(
        id                   = uuid.uuid4(),
        user_id              = client.id,
        visa_type_id         = visa_type.id,
        case_origin          = "lawyer_initiated",
        status               = "in_progress",
        current_stage        = "profile_eligibility",
        due_date             = data.target_date,
        is_draft             = False,
        assigned_attorney_id = attorney_user_id,
        notes                = f"{data.case_name} (priority: {data.priority})",
        created_by           = attorney_user_id,
        modified_by          = attorney_user_id,
    )
    await db_create(db, application)

    # ── 4. Status history row ────────────────────────────────────────────
    await db_create(db, ApplicationStatusHistory(
        application_id = application.id,
        stage          = "profile_eligibility",
        status         = "in_progress",
        note           = "Case created by attorney after consultation.",
        changed_by     = attorney_user_id,
        created_by     = attorney_user_id,
        modified_by    = attorney_user_id,
    ))

    # ── 5. Notifications for both parties ────────────────────────────────
    try:
        await send_email(
            to=client.email,
            subject=f"A new case has been created for you — {visa_type.name}",
            body=(
                f"Hi {client.first_name},\n\n"
                f"Your attorney has created a new {visa_type.name} case for you.\n"
                f"Case number: {application.application_number}\n\n"
                f"Log in to your Vyuflo portal to see next steps.\n\n"
                f"Thanks,\nVyuflo Team"
            ),
        )
        db.add(Notification(
            id=uuid.uuid4(),
            user_id=attorney_user_id,
            notification_type="case_status_updated",
            category="case_update",
            priority="medium",
            title=f"Case created for {client.first_name} {client.last_name}",
            body=f"{visa_type.name} · Priority: {data.priority}.",
            application_id=application.id,
            actor_id=client.id,
            actor_label=f"{client.first_name} {client.last_name}",
            is_read=False,
            created_by=attorney_user_id,
        ))
        db.add(Notification(
            id=uuid.uuid4(),
            user_id=client.id,
            notification_type="case_status_updated",
            category="case_update",
            priority="medium",
            title="Your attorney created a new case",
            body=f"{visa_type.name} case. Your attorney will guide you through next steps.",
            application_id=application.id,
            actor_id=attorney_user_id,
            is_read=False,
            created_by=attorney_user_id,
        ))
    except Exception as e:
        print(f"[create_lawyer_case] notification failed: {e}")

    await db.flush()
    await db.refresh(application)

    return NewCaseCreateResponse(
        id=application.id,
        case_number=application.application_number,
        case_name=data.case_name,
        status=application.status,
        created_at=application.created_at,
        message="Case created successfully.",
    )


async def list_consulted_clients(
    db: AsyncSession,
    attorney_user_id: uuid.UUID,
) -> List[ConsultedClientOut]:
    stmt = (
        select(User, ConsultationSlot.slot_date, ConsultationSlot.slot_time)
        .join(ConsultationBooking, ConsultationBooking.employee_id == User.id)
        .join(AttorneyProfile, AttorneyProfile.id == ConsultationBooking.attorney_id)
        .join(ConsultationSlot, ConsultationSlot.id == ConsultationBooking.slot_id)
        .where(
            and_(
                AttorneyProfile.user_id == attorney_user_id,
                ConsultationBooking.status.in_(["confirmed", "completed"]),
            )
        )
        .order_by(ConsultationSlot.slot_date.desc(), ConsultationSlot.slot_time.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    seen: set[uuid.UUID] = set()
    clients: List[ConsultedClientOut] = []
    for user, slot_date, slot_time in rows:
        if user.id in seen:
            continue
        seen.add(user.id)
        clients.append(ConsultedClientOut(
            user_id=user.id,
            full_name=f"{user.first_name} {user.last_name}",
            email=user.email,
            last_consulted_iso=datetime.combine(slot_date, slot_time),
            visa_hint=None,
        ))
    return clients


async def file_case(
    db: AsyncSession,
    application_id: uuid.UUID,
    data: FileCaseRequest,
    attorney_user_id: uuid.UUID,
) -> FileCaseResponse:
    application = await db_get_by_id(db, Application, application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    if application.assigned_attorney_id != attorney_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the assigned attorney for this case.",
        )

    application.receipt_number      = data.receipt_number
    application.priority_date       = data.priority_date
    application.case_pipeline_stage = "filed"
    application.submission_date     = datetime.now(timezone.utc)
    application.modified_by         = attorney_user_id
    await db.flush()
    await db.refresh(application)

    await db_create(db, ApplicationStatusHistory(
        application_id = application.id,
        stage          = application.current_stage or "uscis_submission",
        status         = application.status,
        note           = f"Case filed. Receipt #: {data.receipt_number}.",
        changed_by     = attorney_user_id,
        created_by     = attorney_user_id,
        modified_by    = attorney_user_id,
    ))

    try:
        client = await db_get_by_id(db, User, application.user_id)
        await send_email(
            to=client.email,
            subject="Your case has been filed",
            body=(
                f"Hi {client.first_name},\n\n"
                f"Your case has been filed with USCIS.\n"
                f"Receipt number: {data.receipt_number}\n"
                f"Priority date: {data.priority_date.isoformat()}\n\n"
                f"Thanks,\nVyuflo Team"
            ),
        )
        db.add(Notification(
            id=uuid.uuid4(),
            user_id=client.id,
            notification_type="case_status_updated",
            category="case_update",
            priority="medium",
            title="Your case has been filed",
            body=f"Receipt #: {data.receipt_number}. Priority date: {data.priority_date.isoformat()}.",
            application_id=application.id,
            actor_id=attorney_user_id,
            is_read=False,
            created_by=attorney_user_id,
        ))
    except Exception as e:
        print(f"[file_case] email/notification failed: {e}")

    return FileCaseResponse(
        id=application.id,
        receipt_number=application.receipt_number,
        priority_date=application.priority_date,
        case_pipeline_stage=application.case_pipeline_stage,
        message="Case filed successfully.",
    )


# =============================================================================
# record_filing() / list_filings() — supports MULTIPLE distinct
# government filings per case (LCA + petition, etc.), unlike file_case()
# above which only holds one receipt_number/priority_date pair.
# =============================================================================

def _build_filing_response(f: ApplicationFiling) -> FilingResponse:
    return FilingResponse(
        id             = f.id,
        application_id = f.application_id,
        filing_type    = f.filing_type,
        receipt_number = f.receipt_number,
        filed_date     = f.filed_date,
        fee_amount     = float(f.fee_amount) if f.fee_amount is not None else None,
        notes          = f.notes,
        document_id    = f.document_id,
        filed_by       = f.filed_by,
        created_at     = f.created_at,
    )


async def record_filing(
    db: AsyncSession,
    application_id: uuid.UUID,
    data: RecordFilingRequest,
    attorney_user_id: uuid.UUID,
) -> FilingResponse:
    application = await db_get_by_id(db, Application, application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    if application.assigned_attorney_id != attorney_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the assigned attorney for this case.",
        )

    filing = ApplicationFiling(
        id             = uuid.uuid4(),
        application_id = application.id,
        filing_type    = data.filing_type,
        receipt_number = data.receipt_number,
        filed_date     = data.filed_date,
        fee_amount     = data.fee_amount,
        notes          = data.notes,
        document_id    = data.document_id,
        filed_by       = attorney_user_id,
        created_by     = attorney_user_id,
        modified_by    = attorney_user_id,
    )
    await db_create(db, filing)

    if data.filing_type == "petition":
        application.receipt_number = data.receipt_number
        application.priority_date  = data.filed_date
        application.modified_by    = attorney_user_id
        await db.flush()
        await db.refresh(application)

    filing_label = {
        "lca":          "LCA filed with the Department of Labor",
        "petition":     "Petition filed with USCIS",
        "rfe_response": "RFE response filed",
        "appeal":       "Appeal filed",
    }.get(data.filing_type, "Filing recorded")

    await db_create(db, ApplicationStatusHistory(
        application_id = application.id,
        stage          = application.current_stage or "uscis_submission",
        status         = application.status,
        note           = f"{filing_label}. Receipt #: {data.receipt_number}.",
        changed_by     = attorney_user_id,
        created_by     = attorney_user_id,
        modified_by    = attorney_user_id,
    ))

    try:
        client = await db_get_by_id(db, User, application.user_id)

        await send_email(
            to=client.email,
            subject=f"{filing_label} — {client.first_name}",
            body=(
                f"Hi {client.first_name},\n\n"
                f"{filing_label}.\n"
                f"Receipt number: {data.receipt_number}\n"
                f"Filed: {data.filed_date.isoformat()}\n\n"
                f"Thanks,\nVyuflo Team"
            ),
        )
        db.add(Notification(
            id=uuid.uuid4(),
            user_id=client.id,
            notification_type="case_status_updated",
            category="case_update",
            priority="medium",
            title=filing_label,
            body=f"Receipt #: {data.receipt_number}. Filed {data.filed_date.isoformat()}.",
            application_id=application.id,
            actor_id=attorney_user_id,
            is_read=False,
            created_by=attorney_user_id,
        ))

        if application.assigned_hr_id:
            hr_user = await db_get_by_id(db, User, application.assigned_hr_id)
            db.add(Notification(
                id=uuid.uuid4(),
                user_id=application.assigned_hr_id,
                notification_type="case_status_updated",
                category="case_update",
                priority="medium",
                title=f"{filing_label} — {client.first_name} {client.last_name}",
                body=f"Receipt #: {data.receipt_number}. Filed {data.filed_date.isoformat()}.",
                application_id=application.id,
                actor_id=attorney_user_id,
                is_read=False,
                created_by=attorney_user_id,
            ))
            if hr_user:
                await send_email(
                    to=hr_user.email,
                    subject=f"{filing_label} — {client.first_name} {client.last_name}",
                    body=(
                        f"Hi {hr_user.first_name},\n\n"
                        f"{filing_label} for {client.first_name} {client.last_name}.\n"
                        f"Receipt number: {data.receipt_number}\n"
                        f"Filed: {data.filed_date.isoformat()}\n\n"
                        f"Thanks,\nVyuflo Team"
                    ),
                )
    except Exception as e:
        print(f"[record_filing] email/notification failed: {e}")

    return _build_filing_response(filing)


async def list_filings(
    db: AsyncSession,
    application_id: uuid.UUID,
    user_id: uuid.UUID,
) -> FilingListResponse:
    application = await db_get_by_id(db, Application, application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    if user_id not in (application.assigned_attorney_id, application.assigned_hr_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    result = await db.execute(
        select(ApplicationFiling)
        .where(ApplicationFiling.application_id == application_id)
        .order_by(ApplicationFiling.filed_date.desc())
    )
    filings = result.scalars().all()
    items = [_build_filing_response(f) for f in filings]
    return FilingListResponse(items=items, total=len(items))


# =============================================================================
# ATTORNEY TASK CHECKLIST — HR<->attorney task traffic, both directions.
# =============================================================================

def _build_attorney_task_response(task: ApplicationTask) -> AttorneyTaskResponse:
    """
    Unpacks the plain-text description AND target from the packed JSON,
    via the shared task_relay module — same single source of truth as
    hr_task_service.py's _build_response and application_services.py's
    _build_task_response.
    """
    _, plain_text, _, _, _, _, target = unpack_task_description(task.description)
    return AttorneyTaskResponse(
        id=task.id,
        application_id=task.application_id,
        task_name=task.task_name,
        description=plain_text or None,
        is_required=task.is_required,
        is_completed=task.is_completed,
        document_id=task.document_id,
        created_at=task.created_at,
        target=target,
    )


async def list_attorney_tasks(
    db: AsyncSession,
    application_id: uuid.UUID,
    attorney_user_id: uuid.UUID,
) -> AttorneyTaskListResponse:
    """
    GET /lawyer/applications/{id}/tasks

    Shows the attorney THREE kinds of task traffic:
      (a) HR->attorney: assigned_to == "attorney" (unaffected — always
          visible, exactly as before any of this relay work was added)
      (b) attorney->HR->employee->HR->attorney intake loop
          (target="employee"): origin == "attorney" AND relay_status ==
          "sent_to_lawyer" — i.e. the attorney's own intake ask, but ONLY
          once HR has completed the full relay. A task still at
          pending_hr_intake / assigned_to_employee / pending_hr_relay must
          NOT appear here — that's the entire point of the gate.
      (c) NEW — attorney->HR direct (target="hr"): assigned_to == "hr" AND
          origin == "attorney". Visible to the attorney IMMEDIATELY (no
          relay gating at all — there's no employee step to protect),
          so they can track "Awaiting HR" -> "Completed" status.
    """
    application = await db_get_by_id(db, Application, application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    if application.assigned_attorney_id != attorney_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    result = await db.execute(
        select(ApplicationTask)
        .where(ApplicationTask.application_id == application_id)
        .order_by(ApplicationTask.is_completed.asc(), ApplicationTask.sort_order.asc())
    )
    all_tasks = result.scalars().all()

    visible = []
    for t in all_tasks:
        _, _, _, assigned_to, relay_status, origin, target = unpack_task_description(t.description)
        if assigned_to == "attorney":
            visible.append(t)
        elif origin == "attorney" and assigned_to == "hr":
            # target="hr" direct request — no gating, always visible.
            visible.append(t)
        elif origin == "attorney" and relay_status == "sent_to_lawyer":
            visible.append(t)

    items = [_build_attorney_task_response(t) for t in visible]
    return AttorneyTaskListResponse(items=items, total=len(items))


async def complete_attorney_task(
    db: AsyncSession,
    application_id: uuid.UUID,
    task_id: uuid.UUID,
    data: CompleteAttorneyTaskRequest,
    attorney_user_id: uuid.UUID,
) -> AttorneyTaskResponse:
    """
    PATCH /lawyer/applications/{id}/tasks/{task_id}/complete
    """
    application = await db_get_by_id(db, Application, application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    if application.assigned_attorney_id != attorney_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    task = await db_get_by_id(db, ApplicationTask, task_id)
    if task:
        _, _, _, assigned_to, _, _, _ = unpack_task_description(task.description)
    else:
        assigned_to = ""
    if not task or task.application_id != application_id or assigned_to != "attorney":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")

    task.is_completed = True
    task.completed_at = datetime.now(timezone.utc)
    task.completed_by = attorney_user_id
    task.document_id  = data.document_id
    task.modified_by  = attorney_user_id
    await db.flush()
    await db.refresh(task)

    try:
        if application.assigned_hr_id:
            db.add(Notification(
                id=uuid.uuid4(),
                user_id=application.assigned_hr_id,
                notification_type="case_status_updated",
                category="case_update",
                priority="medium",
                title="Attorney uploaded a requested document",
                body=task.task_name,
                application_id=application_id,
                actor_id=attorney_user_id,
                is_read=False,
                created_by=attorney_user_id,
            ))
    except Exception as e:
        print(f"[complete_attorney_task] notification failed: {e}")

    return _build_attorney_task_response(task)


async def attorney_create_task(
    db: AsyncSession,
    application_id: uuid.UUID,
    payload: AttorneyTaskCreateRequest,
    attorney_user_id: uuid.UUID,
) -> AttorneyTaskResponse:
    """
    POST /lawyer/applications/{id}/tasks

    Lawyer creates an intake-style ask. Branches on payload.target:

      target="employee" (default) — forced into origin="attorney",
        relay_status="pending_hr_intake", assigned_to="employee". HR must
        review and push it forward (hr_assign_intake_task) before the
        employee ever sees it, and the attorney won't see it back in
        their own list_attorney_tasks() until the full HR relay completes.

      target="hr" — forced into origin="attorney", assigned_to="hr",
        relay_status="sent_to_lawyer" (unused for this target — no gating
        applies). Visible to HR immediately in their task list, and to
        the attorney immediately too (list_attorney_tasks shows target="hr"
        tasks unconditionally). HR completes it directly via the ordinary
        hr_complete_task() — no employee involvement, no relay steps.
    """
    application = await db_get_by_id(db, Application, application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    if application.assigned_attorney_id != attorney_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    if not application.assigned_hr_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This case has no assigned HR user — intake requests require an HR middle step.",
        )

    if payload.target == "hr":
        assigned_to  = "hr"
        relay_status = "sent_to_lawyer"   # no gating applies to this target
    else:
        assigned_to  = "employee"
        relay_status = "pending_hr_intake"

    description_json = json.dumps({
        "priority":     payload.priority,
        "text":         payload.description or "",
        "due_date":     payload.due_date.isoformat() if payload.due_date else None,
        "assigned_to":  assigned_to,
        "relay_status": relay_status,
        "origin":       "attorney",
        "target":       payload.target,
    }, ensure_ascii=False)

    task = ApplicationTask(
        application_id = application_id,
        task_name      = payload.task_name,
        description    = description_json,
        is_required    = payload.is_required,
        is_completed   = False,
        sort_order     = payload.sort_order,
        created_by     = attorney_user_id,
    )
    await db_create(db, task)
    await db.flush()
    await db.refresh(task)

    # Notify HR — mirrors document_request_service's pending_hr_approval notify.
    try:
        title = (
            f"Attorney requested (direct): {payload.task_name}"
            if payload.target == "hr"
            else f"Attorney requested: {payload.task_name}"
        )
        body = (
            "This is for you to handle directly — no employee involvement needed."
            if payload.target == "hr"
            else "Review and assign to the employee."
        )
        db.add(Notification(
            id=uuid.uuid4(),
            user_id=application.assigned_hr_id,
            notification_type="case_status_updated",
            category="case_update",
            priority="medium",
            title=title,
            body=body,
            application_id=application_id,
            actor_id=attorney_user_id,
            created_by=attorney_user_id,
        ))
    except Exception as e:
        print(f"[attorney_create_task] notification failed: {e}")

    return _build_attorney_task_response(task)