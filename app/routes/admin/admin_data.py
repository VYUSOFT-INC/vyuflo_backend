"""
Admin Data browser routes (RBAC P2).

    GET    /api/v1/admin/data/tables
    GET    /api/v1/admin/data/{table}
    POST   /api/v1/admin/data/{table}
    GET    /api/v1/admin/data/{table}/{id}
    PATCH  /api/v1/admin/data/{table}/{id}
    DELETE /api/v1/admin/data/{table}/{id}
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.core.core_permissions import PermissionChecker
from app.core.dependencies import CurrentUserData, DBSession
from app.schemas.admin.admin_data import (
    AdminDataRowResponse,
    AdminDataRowsResponse,
    AdminDataRowWriteRequest,
    AdminDataTablesResponse,
    AdminDataTableMeta,
)
from app.services.admin import admin_data_service as svc

admin_data_router = APIRouter(prefix="/admin/data", tags=["Admin — Data Browser"])


@admin_data_router.get(
    "/tables",
    response_model=AdminDataTablesResponse,
    summary="List allowlisted tables with column metadata",
)
async def get_tables(
    db: DBSession,
    _: CurrentUserData = Depends(PermissionChecker("admin.data.manage")),
) -> AdminDataTablesResponse:
    tables = await svc.list_tables(db)
    return AdminDataTablesResponse(tables=[AdminDataTableMeta(**t) for t in tables])


@admin_data_router.get(
    "/{table_name}",
    response_model=AdminDataRowsResponse,
    summary="Paginated rows for a table",
)
async def get_table_rows(
    table_name: str,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    q: Optional[str] = Query(None, description="Search across string columns"),
    _: CurrentUserData = Depends(PermissionChecker("admin.data.manage")),
) -> AdminDataRowsResponse:
    data = await svc.list_rows(db, table_name, page=page, page_size=page_size, q=q)
    return AdminDataRowsResponse(**data)


@admin_data_router.post(
    "/{table_name}",
    response_model=AdminDataRowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a row",
)
async def create_table_row(
    table_name: str,
    body: AdminDataRowWriteRequest,
    db: DBSession,
    current_user: CurrentUserData = Depends(PermissionChecker("admin.data.manage")),
) -> AdminDataRowResponse:
    data = await svc.create_row(db, table_name, body.data, current_user.user_id)
    return AdminDataRowResponse(**data)


@admin_data_router.get(
    "/{table_name}/{row_id}",
    response_model=AdminDataRowResponse,
    summary="Get a single row by primary key",
)
async def get_table_row(
    table_name: str,
    row_id: str,
    db: DBSession,
    _: CurrentUserData = Depends(PermissionChecker("admin.data.manage")),
) -> AdminDataRowResponse:
    data = await svc.get_row(db, table_name, row_id)
    return AdminDataRowResponse(**data)


@admin_data_router.patch(
    "/{table_name}/{row_id}",
    response_model=AdminDataRowResponse,
    summary="Update a row",
)
async def patch_table_row(
    table_name: str,
    row_id: str,
    body: AdminDataRowWriteRequest,
    db: DBSession,
    current_user: CurrentUserData = Depends(PermissionChecker("admin.data.manage")),
) -> AdminDataRowResponse:
    data = await svc.update_row(db, table_name, row_id, body.data, current_user.user_id)
    return AdminDataRowResponse(**data)


@admin_data_router.delete(
    "/{table_name}/{row_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a row",
)
async def delete_table_row(
    table_name: str,
    row_id: str,
    db: DBSession,
    current_user: CurrentUserData = Depends(PermissionChecker("admin.data.manage")),
) -> None:
    await svc.delete_row(db, table_name, row_id, current_user.user_id)
