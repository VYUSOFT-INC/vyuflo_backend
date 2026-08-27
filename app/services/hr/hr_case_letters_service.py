# app/services/hr/hr_case_letters_service.py
"""
HR-side actions on attorney-generated letters (Generated Letters tab).

Scope for this pass, per current instructions: list / sign / download only.
Deliberately does NOT include:
  - Attorney-side letter generation (creates the draft ApplicationGeneratedLetter
    row in the first place) — that's a separate, attorney-facing feature.
  - The "send to attorney" gate (HR must approve the case before an attorney
    can be looped in) — flagged earlier in this thread, to be discussed
    separately before it's built.

The list of letters embedded in HRCaseResponse (via hr_case_service) and the
standalone list here share the same query shape — kept as two call sites
rather than one shared helper because the case response needs it inline
during _build_case_response, while this module needs it independently
callable (and cheaper — no need to rebuild the whole case object just to
refresh the letters list after a sign action).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visamodels import Application, ApplicationGeneratedLetter, User
from app.schemas.hr.hr_case_schemas import GeneratedLetterInfo
from app.services.employee.services import db_get_by_id, db_update


# =============================================================================
# HELPERS
# =============================================================================

async def _assert_hr_owns_case(
    db: AsyncSession,
    application_id: uuid.UUID,
    hr_user_id: uuid.UUID,
) -> Application:
    """Re-declared here (same pattern as hr_task_service.py) to avoid a
    circular import with hr_case_service."""
    result = await db.execute(select(Application).where(Application.id == application_id))
    app = result.scalars().first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case {application_id} not found.")
    if app.assigned_hr_id != hr_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this case.")
    return app


async def _to_response(db: AsyncSession, letter: ApplicationGeneratedLetter) -> GeneratedLetterInfo:
    gen_by_user = await db_get_by_id(db, User, letter.generated_by_user_id)
    gen_by_name = f"{gen_by_user.first_name} {gen_by_user.last_name}".strip() if gen_by_user else "Attorney"
    return GeneratedLetterInfo(
        id           = letter.id,
        name         = letter.name,
        letter_type  = letter.letter_type,
        generated_by = gen_by_name,
        generated_at = letter.generated_at,
        status       = letter.status,
        file_url     = (
            f"/api/v1/hr/cases/{letter.application_id}/letters/{letter.id}/pdf"
            if letter.file_path else None
        ),
    )


async def _get_letter_or_404(
    db: AsyncSession,
    application_id: uuid.UUID,
    letter_id: uuid.UUID,
) -> ApplicationGeneratedLetter:
    result = await db.execute(
        select(ApplicationGeneratedLetter).where(ApplicationGeneratedLetter.id == letter_id)
    )
    letter = result.scalars().first()
    if not letter or letter.application_id != application_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Letter {letter_id} not found for case {application_id}.",
        )
    return letter


# =============================================================================
# LIST
# =============================================================================

async def hr_list_case_letters(
    db: AsyncSession,
    application_id: uuid.UUID,
    hr_user_id: uuid.UUID,
) -> List[GeneratedLetterInfo]:
    await _assert_hr_owns_case(db, application_id, hr_user_id)

    result = await db.execute(
        select(ApplicationGeneratedLetter)
        .where(ApplicationGeneratedLetter.application_id == application_id)
        .order_by(ApplicationGeneratedLetter.generated_at.desc())
    )
    letters = result.scalars().all()
    return [await _to_response(db, letter) for letter in letters]


# =============================================================================
# SIGN
# =============================================================================

async def hr_sign_case_letter(
    db: AsyncSession,
    application_id: uuid.UUID,
    letter_id: uuid.UUID,
    hr_user_id: uuid.UUID,
) -> GeneratedLetterInfo:
    await _assert_hr_owns_case(db, application_id, hr_user_id)
    letter = await _get_letter_or_404(db, application_id, letter_id)

    if letter.status != "pending_hr_signature":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Letter is '{letter.status}', not 'pending_hr_signature' — "
                "only letters awaiting signature can be signed."
            ),
        )

    await db_update(db, ApplicationGeneratedLetter, letter_id, {
        "status":            "signed",
        "signed_by_user_id": hr_user_id,
        "signed_at":         datetime.now(timezone.utc),
        "modified_by":       hr_user_id,
    })

    refreshed = await _get_letter_or_404(db, application_id, letter_id)
    return await _to_response(db, refreshed)


# =============================================================================
# FILE RESOLUTION (used by the download route)
# =============================================================================

async def hr_get_case_letter_file_path(
    db: AsyncSession,
    application_id: uuid.UUID,
    letter_id: uuid.UUID,
    hr_user_id: uuid.UUID,
) -> str:
    """
    Returns the raw file_path for the route to stream. Kept separate from
    _to_response so the route layer decides HOW to serve it (local
    FileResponse vs. redirecting to an S3 signed URL) without this service
    needing to know about either.
    """
    await _assert_hr_owns_case(db, application_id, hr_user_id)
    letter = await _get_letter_or_404(db, application_id, letter_id)

    if not letter.file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No PDF attached to this letter yet.")

    return letter.file_path
