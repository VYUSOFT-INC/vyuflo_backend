"""
document_field_config_service.py
=================================
Reads and manages the admin-configured, per-document-type OCR field
configuration from the document_field_configurations table.

Scope: fixed-format document types only (passport, i797, i94, ead, lca,
aadhaar, pan) — the ones deterministic_extractor.py handles with stable,
known field names. Fuzzy/VLM-extracted types have no rows here.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visamodels import DocumentFieldConfiguration
from app.services.employee.services import db_create, db_update, db_delete, db_get_by_id


class DocumentFieldConfig(BaseModel):
    mandatory_fields: list[str]
    expiry_field_name: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# READ
# ─────────────────────────────────────────────────────────────────────────────

async def get_document_field_config(
    db: AsyncSession,
    ocr_slug: str,
) -> Optional[DocumentFieldConfig]:
    """
    Config for a single document type by its ocr_slug (e.g. "passport",
    "i797", "ead"). Returns None if no rows exist for this slug — callers
    must treat that as "no fixed-format expectation."
    """
    result = await db.execute(
        select(DocumentFieldConfiguration)
        .where(DocumentFieldConfiguration.ocr_slug == ocr_slug)
        .order_by(DocumentFieldConfiguration.display_order.asc())
    )
    rows = result.scalars().all()
    if not rows:
        return None

    mandatory_fields = [r.field_name for r in rows if r.is_mandatory]
    expiry_row = next((r for r in rows if r.is_expiry_field), None)

    return DocumentFieldConfig(
        mandatory_fields=mandatory_fields,
        expiry_field_name=expiry_row.field_name if expiry_row else None,
    )


async def get_all_document_field_configs(db: AsyncSession) -> dict[str, DocumentFieldConfig]:
    """All configured document types at once, keyed by ocr_slug."""
    result = await db.execute(
        select(DocumentFieldConfiguration)
        .order_by(DocumentFieldConfiguration.ocr_slug, DocumentFieldConfiguration.display_order)
    )
    rows = result.scalars().all()

    by_slug: dict[str, list[DocumentFieldConfiguration]] = {}
    for r in rows:
        by_slug.setdefault(r.ocr_slug, []).append(r)

    return {
        slug: DocumentFieldConfig(
            mandatory_fields=[r.field_name for r in slug_rows if r.is_mandatory],
            expiry_field_name=next((r.field_name for r in slug_rows if r.is_expiry_field), None),
        )
        for slug, slug_rows in by_slug.items()
    }


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN CRUD
# ─────────────────────────────────────────────────────────────────────────────

async def create_document_field_config(
    db: AsyncSession,
    ocr_slug: str,
    field_name: str,
    is_mandatory: bool,
    is_expiry_field: bool,
    display_order: int,
    user_id: uuid.UUID,
) -> DocumentFieldConfiguration:
    """Admin adds a new field. Guards against duplicate (ocr_slug, field_name)
    at the application layer, on top of the DB unique constraint."""
    existing = await db.execute(
        select(DocumentFieldConfiguration).where(
            DocumentFieldConfiguration.ocr_slug == ocr_slug,
            DocumentFieldConfiguration.field_name == field_name,
        ).limit(1)
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=409,
            detail=f"Field '{field_name}' already configured for '{ocr_slug}'.",
        )

    config_row = DocumentFieldConfiguration(
        ocr_slug=ocr_slug,
        field_name=field_name,
        is_mandatory=is_mandatory,
        is_expiry_field=is_expiry_field,
        display_order=display_order,
        created_by=user_id,
    )
    return await db_create(db, config_row)


async def update_document_field_config(
    db: AsyncSession,
    config_id: uuid.UUID,
    user_id: uuid.UUID,
    is_mandatory: Optional[bool] = None,
    is_expiry_field: Optional[bool] = None,
    display_order: Optional[int] = None,
) -> DocumentFieldConfiguration:
    """Partial update — only touches fields the admin actually changed."""
    existing = await db_get_by_id(db, DocumentFieldConfiguration, config_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Field configuration not found.")

    updates: dict = {"modified_by": user_id}
    if is_mandatory is not None:
        updates["is_mandatory"] = is_mandatory
    if is_expiry_field is not None:
        updates["is_expiry_field"] = is_expiry_field
    if display_order is not None:
        updates["display_order"] = display_order

    await db_update(db, DocumentFieldConfiguration, config_id, updates)
    return await db_get_by_id(db, DocumentFieldConfiguration, config_id)


async def delete_document_field_config(
    db: AsyncSession,
    config_id: uuid.UUID,
) -> None:
    existing = await db_get_by_id(db, DocumentFieldConfiguration, config_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Field configuration not found.")
    await db_delete(db, DocumentFieldConfiguration, config_id)
    await db.commit()