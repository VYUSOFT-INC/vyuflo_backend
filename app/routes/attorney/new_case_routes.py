

from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUserData, get_current_user
from app.schemas.attorney.new_case_schemas import (
    NewCaseCreateRequest,
    NewCaseCreateResponse,
    ConsultedClientOut,
    FileCaseRequest,
    FileCaseResponse,
)
from app.services.attorney.new_case_service import (
    create_lawyer_case,
    list_consulted_clients,
    file_case,
)

new_case_router = APIRouter(tags=["Lawyer New Case"])


def _require_attorney(current_user: CurrentUserData) -> None:
    if "attorney" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only attorneys can create cases from the marketplace wizard.",
        )


@new_case_router.post(
    "/lawyer/cases",
    response_model=NewCaseCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attorney creates a new case for a consulted client",
)
async def api_create_lawyer_case(
    body: NewCaseCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserData = Depends(get_current_user),
):
    _require_attorney(current_user)
    result = await create_lawyer_case(db, body, attorney_user_id=current_user.user_id)
    await db.commit()
    return result


@new_case_router.get(
    "/lawyer/consulted-clients",
    response_model=List[ConsultedClientOut],
    summary="List clients this attorney has completed a consultation with",
)
async def api_list_consulted_clients(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserData = Depends(get_current_user),
):
    _require_attorney(current_user)
    return await list_consulted_clients(db, attorney_user_id=current_user.user_id)

@new_case_router.patch(
    "/lawyer/applications/{application_id}/file",
    response_model=FileCaseResponse,
    summary="Attorney records receipt number + priority date once a case is filed",
)
async def api_file_case(
    application_id: uuid.UUID,
    body: FileCaseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserData = Depends(get_current_user),
):
    _require_attorney(current_user)
    result = await file_case(db, application_id, body, attorney_user_id=current_user.user_id)
    await db.commit()
    return result