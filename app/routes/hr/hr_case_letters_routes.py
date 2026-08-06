# app/routes/hr_case_letters_routes.py
#
# HR-side Generated Letters endpoints (Generated Letters tab).
# HR-owned namespace, per the employee → HR → (optionally) attorney workflow —
# HR is the access-control root, same as every other /hr/cases/{id}/... route.
#
# Mount in main.py ALONGSIDE hr_case_router:
#   from app.routes.hr_case_letters_routes import hr_case_letters_router
#   app.include_router(hr_case_letters_router, prefix="/api/v1/hr", tags=["HR Case Letters"])
#
# Endpoints:
#   GET   /api/v1/hr/cases/{application_id}/letters
#   POST  /api/v1/hr/cases/{application_id}/letters/{letter_id}/sign
#   GET   /api/v1/hr/cases/{application_id}/letters/{letter_id}/pdf
#
# NOT included in this pass (out of scope per current instructions):
#   - attorney-side letter generation
#   - POST .../letters/request (gated behind the HR-approval → send-to-attorney
#     workflow discussed separately)

import os
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.hr.hr_case_schemas import GeneratedLetterInfo
from app.services.hr.hr_case_letters_service import (
    hr_get_case_letter_file_path,
    hr_list_case_letters,
    hr_sign_case_letter,
)

hr_case_letters_router = APIRouter()


@hr_case_letters_router.get(
    "/cases/{application_id}/letters",
    response_model=List[GeneratedLetterInfo],
    summary="HR: List all letters generated for this case",
)
async def api_hr_list_case_letters(
    application_id: uuid.UUID,
    db:             AsyncSession = Depends(get_db),
    current_user                 = Depends(get_current_user),
) -> List[GeneratedLetterInfo]:
    return await hr_list_case_letters(db, application_id, current_user.user_id)


@hr_case_letters_router.post(
    "/cases/{application_id}/letters/{letter_id}/sign",
    response_model=GeneratedLetterInfo,
    summary="HR: Sign a letter (transitions status to 'signed')",
    description="Only letters in 'pending_hr_signature' status can be signed.",
)
async def api_hr_sign_case_letter(
    application_id: uuid.UUID,
    letter_id:      uuid.UUID,
    db:             AsyncSession = Depends(get_db),
    current_user                 = Depends(get_current_user),
) -> GeneratedLetterInfo:
    return await hr_sign_case_letter(db, application_id, letter_id, current_user.user_id)


@hr_case_letters_router.get(
    "/cases/{application_id}/letters/{letter_id}/pdf",
    summary="HR: Download a generated letter as PDF",
    description=(
        "Streams the PDF if file_path is a local path. If your deployment "
        "stores letters in S3, swap the FileResponse below for a redirect "
        "to a signed URL — hr_get_case_letter_file_path() already returns "
        "the raw file_path either way, this route just decides how to serve it."
    ),
)
async def api_hr_download_case_letter(
    application_id: uuid.UUID,
    letter_id:      uuid.UUID,
    db:             AsyncSession = Depends(get_db),
    current_user                 = Depends(get_current_user),
):
    file_path = await hr_get_case_letter_file_path(db, application_id, letter_id, current_user.user_id)

    local_path = f"./{file_path}"
    if not os.path.exists(local_path):
        raise HTTPException(status_code=404, detail="File not found on disk.")

    return FileResponse(
        path       = local_path,
        media_type = "application/pdf",
        filename   = os.path.basename(local_path),
        headers    = {"Content-Disposition": "inline"},
    )
