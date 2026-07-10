from __future__ import annotations
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.employee.visa_type import VisaTypeListResponse, VisaTypeResponse
from app.services.employee.visa_type_service import get_visa_type, list_visa_types
# from app.core.auth import get_current_user  # uncomment if auth required

visa_type_router = APIRouter()


@visa_type_router.get(
    "/visa-types",
    response_model=VisaTypeListResponse,
    status_code=status.HTTP_200_OK,
    summary="List visa types",
    description=(
        "Returns all active visa types for populating dropdowns and selection "
        "screens. Filter by category (employment, student, visitor, etc.)."
    ),
)
async def list_visa_types_endpoint(
    category: Optional[str] = Query(
        None,
        description="Filter by category: employment | student | visitor | "
                    "permanent_resident | exchange",
    ),
    active_only: bool = Query(True, description="Return only active visa types"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
) -> VisaTypeListResponse:
    items, total = await list_visa_types(
        db,
        category=category,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )
    return VisaTypeListResponse(
        items=[VisaTypeResponse.model_validate(r) for r in items],
        total=total,
    )


@visa_type_router.get(
    "/visa-types/{visa_type_id}",
    response_model=VisaTypeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a single visa type by ID",
    description="Returns full visa type details including required_documents list.",
)
async def api_get_visa_type(
    visa_type_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user),
) -> VisaTypeResponse:
    visa_type = await get_visa_type(db, visa_type_id)
    return VisaTypeResponse.model_validate(visa_type)