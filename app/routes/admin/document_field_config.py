# ─────────────────────────────────────────────────────────────────────────────
# NEW FILE — app/routes/admin/document_field_config.py
#
# NOTE: I'm following the DBSession / Current_User / RoleChecker pattern
# from your other admin routers based on what I know of your dependency
# structure (app/core/dependencies.py, app/core/permissions.py). If your
# actual admin-guard dependency has a different name/signature, swap it in
# — the CRUD logic itself doesn't depend on which guard wraps it.
# ─────────────────────────────────────────────────────────────────────────────

import uuid
from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.core.dependencies import Current_User, DBSession
from app.core.core_permissions import RoleChecker  # adjust import path if different
from app.models.visamodels import DocumentFieldConfiguration
from app.schemas.admin.document_field_config import (
    DocumentFieldConfigCreateRequest,
    DocumentFieldConfigUpdateRequest,
    DocumentFieldConfigResponse,
)
from app.services.employee.document_field_config_service import (
    create_document_field_config,
    update_document_field_config,
    delete_document_field_config,
)

document_field_config_router = APIRouter()

_admin_only = Depends(RoleChecker(["app_admin"]))


@document_field_config_router.get(
    "/admin/document-field-configs",
    response_model=list[DocumentFieldConfigResponse],
    dependencies=[_admin_only],
    summary="List all document field configurations",
    description="Returns every configured field across all fixed-format document types.",
)
async def list_document_field_configs(db: DBSession):
    result = await db.execute(
        select(DocumentFieldConfiguration)
        .order_by(DocumentFieldConfiguration.ocr_slug, DocumentFieldConfiguration.display_order)
    )
    return result.scalars().all()


@document_field_config_router.get(
    "/admin/document-field-configs/{ocr_slug}",
    response_model=list[DocumentFieldConfigResponse],
    dependencies=[_admin_only],
    summary="List field configurations for one document type",
)
async def list_document_field_configs_by_slug(ocr_slug: str, db: DBSession):
    result = await db.execute(
        select(DocumentFieldConfiguration)
        .where(DocumentFieldConfiguration.ocr_slug == ocr_slug)
        .order_by(DocumentFieldConfiguration.display_order)
    )
    return result.scalars().all()


@document_field_config_router.post(
    "/admin/document-field-configs",
    response_model=DocumentFieldConfigResponse,
    status_code=201,
    dependencies=[_admin_only],
    summary="Add a new field configuration",
    description="Admin adds a field to a document type's mandatory/expiry configuration.",
)
async def add_document_field_config(
    payload: DocumentFieldConfigCreateRequest,
    db: DBSession,
    current_user: Current_User,
):
    return await create_document_field_config(
        db,
        ocr_slug=payload.ocr_slug,
        field_name=payload.field_name,
        is_mandatory=payload.is_mandatory,
        is_expiry_field=payload.is_expiry_field,
        display_order=payload.display_order,
        user_id=current_user.user_id,
    )


@document_field_config_router.patch(
    "/admin/document-field-configs/{config_id}",
    response_model=DocumentFieldConfigResponse,
    dependencies=[_admin_only],
    summary="Update a field configuration",
    description="Toggle is_mandatory / is_expiry_field, or reorder, for an existing field.",
)
async def edit_document_field_config(
    config_id: uuid.UUID,
    payload: DocumentFieldConfigUpdateRequest,
    db: DBSession,
    current_user: Current_User,
):
    return await update_document_field_config(
        db,
        config_id=config_id,
        user_id=current_user.user_id,
        is_mandatory=payload.is_mandatory,
        is_expiry_field=payload.is_expiry_field,
        display_order=payload.display_order,
    )


@document_field_config_router.delete(
    "/admin/document-field-configs/{config_id}",
    status_code=204,
    dependencies=[_admin_only],
    summary="Remove a field configuration",
    description="Admin removes a field from a document type's configuration entirely.",
)
async def remove_document_field_config(config_id: uuid.UUID, db: DBSession):
    await delete_document_field_config(db, config_id)