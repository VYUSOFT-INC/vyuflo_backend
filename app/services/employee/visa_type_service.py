from __future__ import annotations
from typing import Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.visamodels import VisaType
from app.services.employee.services import db_get_by_id, db_list


async def list_visa_types(
    db: AsyncSession,
    *,
    category: Optional[str] = None,
    codes: Optional[list[str]] = None,       
    active_only: bool = True,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[VisaType], int]:
    filters = []
    if active_only:
        filters.append(VisaType.is_active == True)
    if category:
        filters.append(VisaType.category == category)
    if codes:                                 
        filters.append(VisaType.code.in_(codes))

    rows = await db_list(
        db,
        VisaType,
        filters=filters or None,
        limit=limit,
        offset=offset,
    )

    from sqlalchemy import select, func
    count_stmt = select(func.count()).select_from(VisaType)
    if filters:
        count_stmt = count_stmt.where(*filters)
    result = await db.execute(count_stmt)
    total = result.scalar_one()

    return list(rows), total

async def get_visa_type(
    db: AsyncSession,
    visa_type_id: uuid.UUID,
) -> VisaType:
    """
    GET /visa-types/{visa_type_id}
    Returns a single visa type by ID.
    Raises 404 if not found or inactive.
    """
    visa_type = await db_get_by_id(db, VisaType, visa_type_id)
    
    if not visa_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Visa type {visa_type_id} not found.",
        )
    
    if not visa_type.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Visa type {visa_type_id} is not active.",
        )
    
    return visa_type