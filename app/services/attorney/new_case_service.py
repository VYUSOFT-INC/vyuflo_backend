from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.email import send_email

from app.models.visamodels import (
    User,
    Application,
    ApplicationStatusHistory,
    VisaType,
    AttorneyProfile,
    ConsultationBooking,
    ConsultationSlot,
    Notification,
)
from app.schemas.attorney.new_case_schemas import (
    NewCaseCreateRequest,
    NewCaseCreateResponse,
    ConsultedClientOut,
    FileCaseRequest,      # NEW
    FileCaseResponse,     # NEW
)
from app.services.employee.services import db_create, db_get_by_id
from app.core.email import send_email


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
    # Uses your REAL Notification columns (no `payload` field exists, and
    # "case" isn't a valid category or notification_type — using the closest
    # real enum values instead: category="case_update",
    # notification_type="case_status_updated").
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
    # NOTE: doc 3 assumed a `ConsultationBooking.scheduled_start_iso` column —
    # that column doesn't exist. The real date/time lives on the linked
    # ConsultationSlot (slot_date + slot_time), so we join through it instead.
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
        if user.id in seen:      # keep only the most recent booking per client
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
    # ── 1. Load + ownership check ────────────────────────────────────────
    application = await db_get_by_id(db, Application, application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    if application.assigned_attorney_id != attorney_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the assigned attorney for this case.",
        )

    # ── 2. Record filing details ─────────────────────────────────────────
    application.receipt_number      = data.receipt_number
    application.priority_date       = data.priority_date
    application.case_pipeline_stage = "filed"
    application.submission_date     = datetime.now(timezone.utc)
    application.modified_by         = attorney_user_id
    await db.flush()
    await db.refresh(application)

    # ── 3. Status history entry ──────────────────────────────────────────
    await db_create(db, ApplicationStatusHistory(
        application_id = application.id,
        stage          = application.current_stage or "uscis_submission",
        status         = application.status,
        note           = f"Case filed. Receipt #: {data.receipt_number}.",
        changed_by     = attorney_user_id,
        created_by     = attorney_user_id,
        modified_by    = attorney_user_id,
    ))

    # ── 4. Email + notification to the client ────────────────────────────
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