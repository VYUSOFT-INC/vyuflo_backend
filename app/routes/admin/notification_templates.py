"""
app/routes/notification_templates.py  ← FINAL CORRECT VERSION
Replace your existing app/routes/notification_templates.py with this.

Matches the Notification Templates screen exactly:
  - List with name, channel badge, trigger event, last modified (+ by name), status toggle
  - Search by template name
  - Filter: All Channels | All Triggers | All Statuses
  - Pagination: "Showing 1 to 10 of 24 results"
  - Create Template button
  - Status toggle per row

Endpoints:
  POST   /notification-templates                         — Create Template button
  GET    /notification-templates                         — list with search/filter/pagination
  GET    /notification-templates/by-key/{event_key}      — get by trigger key
  GET    /notification-templates/{template_id}           — get by ID
  PATCH  /notification-templates/{template_id}           — update content
  PATCH  /notification-templates/{template_id}/toggle    — Status toggle switch
  POST   /notification-templates/{template_id}/preview   — preview rendered template
  DELETE /notification-templates/{template_id}           — soft-delete (is_active=False)
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Query, status

from app.core.dependencies import Current_User, DBSession
from app.core.core_permissions import PermissionChecker
from app.schemas.admin.notification_template import (
    NotificationTemplateCreate,
    NotificationTemplateListResponse,
    NotificationTemplateResponse,
    NotificationTemplateToggle,
    NotificationTemplateUpdate,
)
from app.services.admin.notification_template import (
    service_create_template,
    service_get_template,
    service_get_template_by_event_key,
    service_list_templates,
    service_preview_template,
    service_toggle_template,
    service_update_template,
)

notification_templates_router = APIRouter()
_require = PermissionChecker("notifications.manage")


def _to_response(t) -> NotificationTemplateResponse:
    """Build response, injecting last_modified_by_name from the temp attribute."""
    r = NotificationTemplateResponse.model_validate(t)
    # Inject the computed name set in service_list_templates
    if hasattr(t, "_last_modified_by_name"):
        object.__setattr__(r, "last_modified_by_name", t._last_modified_by_name)
    return r


# =============================================================================
# POST /notification-templates — "Create Template" button
# =============================================================================
@notification_templates_router.post(
    "/notification-templates",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new notification template",
)
async def create_template(
    payload:      NotificationTemplateCreate,
    db:           DBSession,
    current_user: Current_User,
    _:            Current_User = _require,
) -> NotificationTemplateResponse:
    t = await service_create_template(
        db=db,
        event_key=payload.event_key, name=payload.name, description=payload.description,
        channel=payload.channel, subject=payload.subject, body_html=payload.body_html,
        body_text=payload.body_text, available_placeholders=payload.available_placeholders,
        category=payload.category, is_active=payload.is_active,
        created_by=current_user.user_id,
    )
    return NotificationTemplateResponse.model_validate(t)


# =============================================================================
# GET /notification-templates — Main list screen
# Filters: All Channels | All Triggers | All Statuses
# Pagination: "Showing 1 to 10 of 24 results"
# =============================================================================
@notification_templates_router.get(
    "/notification-templates",
    status_code=status.HTTP_200_OK,
    summary="List notification templates",
    description=(
        "Powers the Notification Templates list screen. "
        "Filter by channel (email/sms/in_app/push), "
        "trigger event key (partial match), "
        "or status (active/inactive). "
        "Search by template name, event_key, or description."
    ),
)
async def list_templates(
    db:        DBSession,
    _:         Current_User = _require,
    channel:   Optional[str]  = Query(None, description="email | sms | in_app | push"),
    trigger:   Optional[str]  = Query(None, description="Partial event_key match e.g. 'status_changed'"),
    is_active: Optional[bool] = Query(None, description="true=active, false=inactive"),
    search:    Optional[str]  = Query(None, min_length=2, description="Search name, trigger, or description"),
    page:      int            = Query(1,  ge=1),
    limit:     int            = Query(10, ge=1, le=100),
) -> NotificationTemplateListResponse:
    result = await service_list_templates(
        db=db, channel=channel, trigger=trigger,
        is_active=is_active, search=search, page=page, limit=limit,
    )
    return NotificationTemplateListResponse(
        items=[_to_response(t) for t in result["items"]],
        total=result["total"],
        page=result["page"],
        limit=result["limit"],
        total_pages=result["total_pages"],
    )


# =============================================================================
# GET /notification-templates/by-key/{event_key}
# MUST be before /{template_id} to prevent FastAPI treating "by-key" as UUID
# =============================================================================
@notification_templates_router.get(
    "/notification-templates/by-key/{event_key}",
    status_code=status.HTTP_200_OK,
    summary="Get a template by trigger event key",
)
async def get_template_by_key(
    event_key: str,
    db:        DBSession,
    _:         Current_User = _require,
) -> NotificationTemplateResponse:
    t = await service_get_template_by_event_key(db, event_key)
    return NotificationTemplateResponse.model_validate(t)


# =============================================================================
# GET /notification-templates/{template_id}
# =============================================================================
@notification_templates_router.get(
    "/notification-templates/{template_id}",
    status_code=status.HTTP_200_OK,
    summary="Get a notification template by ID",
)
async def get_template(
    template_id: uuid.UUID,
    db:          DBSession,
    _:           Current_User = _require,
) -> NotificationTemplateResponse:
    t = await service_get_template(db, template_id)
    return NotificationTemplateResponse.model_validate(t)


# =============================================================================
# PATCH /notification-templates/{template_id}/toggle — Status column toggle
# MUST be declared BEFORE /{template_id} to avoid path collision
# =============================================================================
@notification_templates_router.patch(
    "/notification-templates/{template_id}/toggle",
    status_code=status.HTTP_200_OK,
    summary="Toggle template active/inactive",
    description="The on/off switch in the Status column of the templates list.",
)
async def toggle_template(
    template_id:  uuid.UUID,
    payload:      NotificationTemplateToggle,
    db:           DBSession,
    current_user: Current_User,
    _:            Current_User = _require,
) -> NotificationTemplateResponse:
    t = await service_toggle_template(
        db=db, template_id=template_id,
        is_active=payload.is_active, modified_by=current_user.user_id,
    )
    return NotificationTemplateResponse.model_validate(t)


# =============================================================================
# POST /notification-templates/{template_id}/preview
# MUST be declared BEFORE /{template_id} (PATCH) to avoid route ambiguity
# =============================================================================
@notification_templates_router.post(
    "/notification-templates/{template_id}/preview",
    status_code=status.HTTP_200_OK,
    summary="Preview rendered template with sample context",
    description=(
        "Renders {{placeholders}} with supplied context. "
        "No DB writes, no notifications sent. "
        "Body: { 'user_name': 'John', 'application_number': 'APP-001' }"
    ),
)
async def preview_template(
    template_id: uuid.UUID,
    context:     Dict[str, Any],
    db:          DBSession,
    _:           Current_User = _require,
) -> dict:
    return await service_preview_template(db=db, template_id=template_id, context=context)


# =============================================================================
# PATCH /notification-templates/{template_id} — Edit template content
# =============================================================================
@notification_templates_router.patch(
    "/notification-templates/{template_id}",
    status_code=status.HTTP_200_OK,
    summary="Update notification template content",
    description=(
        "Updates name, description, subject, body_html, body_text, "
        "available_placeholders, is_active. "
        "event_key and channel are immutable after creation."
    ),
)
async def update_template(
    template_id:  uuid.UUID,
    payload:      NotificationTemplateUpdate,
    db:           DBSession,
    current_user: Current_User,
    _:            Current_User = _require,
) -> NotificationTemplateResponse:
    t = await service_update_template(
        db=db, template_id=template_id,
        name=payload.name, description=payload.description,
        subject=payload.subject, body_html=payload.body_html,
        body_text=payload.body_text,
        available_placeholders=payload.available_placeholders,
        is_active=payload.is_active, modified_by=current_user.user_id,
    )
    return NotificationTemplateResponse.model_validate(t)


# =============================================================================
# DELETE /notification-templates/{template_id} — Soft delete only
# Hard delete blocked: event_key is referenced in dispatch service code
# =============================================================================
@notification_templates_router.delete(
    "/notification-templates/{template_id}",
    status_code=status.HTTP_200_OK,
    summary="Disable (soft-delete) a notification template",
    description="Sets is_active=False. Does not hard-delete — event_key must remain stable.",
)
async def delete_template(
    template_id:  uuid.UUID,
    db:           DBSession,
    current_user: Current_User,
    _:            Current_User = _require,
) -> dict:
    await service_toggle_template(
        db=db, template_id=template_id,
        is_active=False, modified_by=current_user.user_id,
    )
    return {"message": "Template disabled successfully."}