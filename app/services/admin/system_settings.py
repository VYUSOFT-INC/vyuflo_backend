"""
app/services/system_settings.py  ← FINAL CORRECT VERSION
Save as: app/services/system_settings.py

Your routes/system_settings.py already imports from this path:
  from app.services.system_settings import (...)
"""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.models.visamodels import SystemSetting


# =============================================================================
# IN-MEMORY CACHE
# Settings are read on every request (feature flags, maintenance mode check).
# Hitting DB every time is wasteful — cache all key→value pairs in a dict.
# Cache is busted (cleared) whenever any setting is written.
# asyncio is single-threaded → no locks needed.
# =============================================================================
_cache: Dict[str, str] = {}
_cache_ready: bool = False


async def _warm_cache(db: AsyncSession) -> None:
    global _cache, _cache_ready
    rows = (await db.execute(select(SystemSetting))).scalars().all()
    _cache = {row.key: row.value for row in rows}
    _cache_ready = True


def _bust_cache() -> None:
    global _cache_ready
    _cache.clear()
    _cache_ready = False


# ── Public helpers (used by middleware + other services) ──────────────────────

async def get_setting_value(db: AsyncSession, key: str) -> Optional[str]:
    """Cache-first read. Returns raw string or None."""
    if not _cache_ready:
        await _warm_cache(db)
    return _cache.get(key)


async def is_feature_enabled(db: AsyncSession, key: str) -> bool:
    """Returns True if setting value == 'true'. Used for feature flag checks."""
    return (await get_setting_value(db, key)) == "true"


async def is_maintenance_mode(db: AsyncSession) -> bool:
    return await is_feature_enabled(db, "maintenance.enabled")


def cast_setting_value(value: str, value_type: str):
    """
    Cast raw stored string to correct Python type.
    Examples:
        cast_setting_value("true", "boolean")  → True
        cast_setting_value("60",   "integer")  → 60
        cast_setting_value('{"a":1}', "json")  → {"a": 1}
    """
    import json as _json
    if value_type == "boolean": return value.lower() == "true"
    if value_type == "integer": return int(value)
    if value_type == "json":    return _json.loads(value)
    return value  # string / url → return as-is


# =============================================================================
# CREATE
# =============================================================================
async def service_create_setting(
    db: AsyncSession, key: str, value: str, value_type: str,
    setting_group: str, label: str, description: Optional[str],
    is_public: bool, is_readonly: bool, display_order: int,
    created_by: uuid.UUID,
) -> SystemSetting:
    exists = (await db.execute(
        select(SystemSetting).where(SystemSetting.key == key)
    )).scalar_one_or_none()
    if exists:
        raise ConflictException(f"Setting key '{key}' already exists.")

    s = SystemSetting(
        key=key, value=value, value_type=value_type,
        setting_group=setting_group, label=label, description=description,
        is_public=is_public, is_readonly=is_readonly,
        display_order=display_order, created_by=created_by, modified_by=created_by,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    _bust_cache()
    return s


# =============================================================================
# LIST  (filterable + optional group-by for tab UI)
# =============================================================================
async def service_list_settings(
    db: AsyncSession,
    setting_group:   Optional[str] = None,
    include_private: bool          = True,
    group_by:        bool          = False,
    search:          Optional[str] = None,
) -> dict:
    stmt = select(SystemSetting).order_by(
        SystemSetting.setting_group, SystemSetting.display_order
    )
    if setting_group:
        stmt = stmt.where(SystemSetting.setting_group == setting_group)
    if not include_private:
        stmt = stmt.where(SystemSetting.is_public == True)
    if search:
        t = f"%{search}%"
        stmt = stmt.where(
            SystemSetting.key.ilike(t) | SystemSetting.label.ilike(t)
        )

    items = (await db.execute(stmt)).scalars().all()

    grouped = None
    if group_by:
        grouped: Dict[str, list] = {}
        for item in items:
            grouped.setdefault(item.setting_group, []).append(item)

    return {"items": items, "total": len(items), "grouped": grouped}


# =============================================================================
# GET BY KEY
# =============================================================================
async def service_get_setting(db: AsyncSession, key: str) -> SystemSetting:
    s = (await db.execute(
        select(SystemSetting).where(SystemSetting.key == key)
    )).scalar_one_or_none()
    if not s:
        raise NotFoundException(f"Setting '{key}' not found.")
    return s


# =============================================================================
# UPDATE BY KEY  (PATCH /settings/{key})
# =============================================================================
async def service_update_setting(
    db: AsyncSession, key: str,
    value: Optional[str], label: Optional[str], description: Optional[str],
    is_public: Optional[bool], is_readonly: Optional[bool],
    display_order: Optional[int], modified_by: uuid.UUID,
) -> SystemSetting:
    s = await service_get_setting(db, key)
    if value         is not None: s.value         = value
    if label         is not None: s.label         = label
    if description   is not None: s.description   = description
    if is_public     is not None: s.is_public     = is_public
    if is_readonly   is not None: s.is_readonly   = is_readonly
    if display_order is not None: s.display_order = display_order
    s.modified_by = modified_by
    await db.commit()
    await db.refresh(s)
    _bust_cache()
    return s


# =============================================================================
# BULK UPDATE  (PATCH /settings/bulk)
# The "Save Changes" button sends all changed fields at once.
# =============================================================================
async def service_bulk_update_settings(
    db: AsyncSession, updates: List[dict], modified_by: uuid.UUID,
) -> List[SystemSetting]:
    keys = [u["key"] for u in updates]
    found = {
        s.key: s for s in (await db.execute(
            select(SystemSetting).where(SystemSetting.key.in_(keys))
        )).scalars().all()
    }
    missing = [k for k in keys if k not in found]
    if missing:
        raise NotFoundException(f"Settings not found: {missing}")
    readonly = [k for k in keys if found[k].is_readonly]
    if readonly:
        raise BadRequestException(f"Read-only settings cannot be updated: {readonly}")

    updated = []
    for u in updates:
        s = found[u["key"]]
        s.value = u["value"]
        s.modified_by = modified_by
        updated.append(s)
    await db.commit()
    for s in updated:
        await db.refresh(s)
    _bust_cache()
    return updated


# =============================================================================
# FEATURE FLAG TOGGLE  (PATCH /settings/toggle-feature/{key})
# Only works on value_type == "boolean" rows (Feature Flags tab)
# =============================================================================
async def service_toggle_feature(
    db: AsyncSession, key: str, enabled: bool, modified_by: uuid.UUID,
) -> SystemSetting:
    s = await service_get_setting(db, key)
    if s.value_type != "boolean":
        raise BadRequestException(
            f"'{key}' is not a boolean flag (value_type={s.value_type})."
        )
    s.value       = "true" if enabled else "false"
    s.modified_by = modified_by
    await db.commit()
    await db.refresh(s)
    _bust_cache()
    return s


# =============================================================================
# MAINTENANCE MODE  (PATCH /settings/maintenance)
# Maintenance tab — toggle + optional banner message update
# =============================================================================
async def service_set_maintenance_mode(
    db: AsyncSession, enabled: bool,
    message: Optional[str], modified_by: uuid.UUID,
) -> dict:
    await service_toggle_feature(db, "maintenance.enabled", enabled, modified_by)
    if message is not None:
        await service_update_setting(
            db=db, key="maintenance.message", value=message,
            label=None, description=None, is_public=None,
            is_readonly=None, display_order=None, modified_by=modified_by,
        )
    return {
        "maintenance_enabled": enabled,
        "message": message or (
            "Maintenance mode enabled." if enabled else "Maintenance mode disabled."
        ),
    }


# =============================================================================
# DELETE  (DELETE /settings/{key})
# =============================================================================
async def service_delete_setting(db: AsyncSession, key: str) -> dict:
    s = await service_get_setting(db, key)
    if s.is_readonly:
        raise BadRequestException(
            f"'{key}' is a core setting (is_readonly=True). Cannot delete."
        )
    await db.delete(s)
    await db.commit()
    _bust_cache()
    return {"message": f"Setting '{key}' deleted successfully."}


# =============================================================================
# SEED DATA — seeded on startup via lifespan in main.py
# Covers all 6 sidebar tabs visible on the General Settings screen
# =============================================================================
SETTINGS_SEED = [
    # ── General Tab — Platform Identity ──────────────────────────────────────
    {"key": "platform.name",            "value": "VisaFlow Enterprise",    "value_type": "string",  "setting_group": "general",       "label": "Platform Name",                  "is_public": True,  "is_readonly": True,  "display_order": 1},
    {"key": "platform.support_email",   "value": "support@visaflow.com",   "value_type": "string",  "setting_group": "general",       "label": "Support Email",                  "is_public": True,  "is_readonly": False, "display_order": 2},
    {"key": "platform.website",         "value": "www.visaflow.com",       "value_type": "url",     "setting_group": "general",       "label": "Company Website",                "is_public": True,  "is_readonly": False, "display_order": 3},
    {"key": "platform.contact_phone",   "value": "+1 (800) 555-0199",      "value_type": "string",  "setting_group": "general",       "label": "Contact Phone",                  "is_public": True,  "is_readonly": False, "display_order": 4},
    # ── General Tab — Regional & Formatting ──────────────────────────────────
    {"key": "platform.timezone",        "value": "America/New_York",       "value_type": "string",  "setting_group": "general",       "label": "Default Timezone",               "is_public": False, "is_readonly": False, "display_order": 5},
    {"key": "platform.language",        "value": "en",                     "value_type": "string",  "setting_group": "general",       "label": "System Language",                "is_public": True,  "is_readonly": False, "display_order": 6},
    {"key": "platform.date_format",     "value": "MM/DD/YYYY",             "value_type": "string",  "setting_group": "general",       "label": "Date Format",                    "is_public": False, "is_readonly": False, "display_order": 7},
    {"key": "platform.currency",        "value": "USD",                    "value_type": "string",  "setting_group": "general",       "label": "Currency Default",               "is_public": True,  "is_readonly": False, "display_order": 8},
    # ── Security & Access Tab ─────────────────────────────────────────────────
    {"key": "security.session_timeout", "value": "60",                     "value_type": "integer", "setting_group": "security",      "label": "Session Timeout (minutes)",      "is_public": False, "is_readonly": False, "display_order": 1},
    {"key": "security.max_login_attempts","value": "5",                    "value_type": "integer", "setting_group": "security",      "label": "Max Login Attempts",             "is_public": False, "is_readonly": False, "display_order": 2},
    {"key": "security.lockout_minutes", "value": "30",                     "value_type": "integer", "setting_group": "security",      "label": "Account Lockout (minutes)",      "is_public": False, "is_readonly": False, "display_order": 3},
    {"key": "security.require_2fa_admin","value": "false",                 "value_type": "boolean", "setting_group": "security",      "label": "Require 2FA for Admins",         "is_public": False, "is_readonly": False, "display_order": 4},
    {"key": "security.password_min_length","value": "8",                   "value_type": "integer", "setting_group": "security",      "label": "Min Password Length",            "is_public": False, "is_readonly": False, "display_order": 5},
    # ── Notifications Tab ─────────────────────────────────────────────────────
    {"key": "notifications.digest_hour","value": "8",                      "value_type": "integer", "setting_group": "notifications", "label": "Daily Digest Send Hour (UTC)",   "is_public": False, "is_readonly": False, "display_order": 1},
    {"key": "notifications.max_per_day","value": "20",                     "value_type": "integer", "setting_group": "notifications", "label": "Max Notifications Per User/Day", "is_public": False, "is_readonly": False, "display_order": 2},
    # ── Feature Flags Tab ─────────────────────────────────────────────────────
    {"key": "features.email_notifications","value": "true",                "value_type": "boolean", "setting_group": "features",      "label": "Email Notifications",            "is_public": False, "is_readonly": False, "display_order": 1},
    {"key": "features.sms_notifications","value": "false",                 "value_type": "boolean", "setting_group": "features",      "label": "SMS Notifications",              "is_public": False, "is_readonly": False, "display_order": 2},
    {"key": "features.push_notifications","value": "true",                 "value_type": "boolean", "setting_group": "features",      "label": "Push Notifications",             "is_public": False, "is_readonly": False, "display_order": 3},
    {"key": "features.news_feed",        "value": "true",                  "value_type": "boolean", "setting_group": "features",      "label": "News Feed",                      "is_public": False, "is_readonly": False, "display_order": 4},
    {"key": "features.interview_prep",   "value": "true",                  "value_type": "boolean", "setting_group": "features",      "label": "Interview Prep Module",          "is_public": False, "is_readonly": False, "display_order": 5},
    {"key": "features.weekly_digest",    "value": "true",                  "value_type": "boolean", "setting_group": "features",      "label": "Weekly Digest Emails",           "is_public": False, "is_readonly": False, "display_order": 6},
    # ── Maintenance Tab ───────────────────────────────────────────────────────
    {"key": "maintenance.enabled",       "value": "false",                 "value_type": "boolean", "setting_group": "maintenance",   "label": "Maintenance Mode",               "is_public": False, "is_readonly": False, "display_order": 1},
    {"key": "maintenance.message",       "value": "We are performing scheduled maintenance. We'll be back shortly.", "value_type": "string", "setting_group": "maintenance", "label": "Maintenance Banner Message", "is_public": True, "is_readonly": False, "display_order": 2},
]


async def seed_system_settings(db: AsyncSession) -> None:
    """Idempotent — safe to call every startup. Skips already-seeded keys."""
    for item in SETTINGS_SEED:
        exists = (await db.execute(
            select(SystemSetting).where(SystemSetting.key == item["key"])
        )).scalar_one_or_none()
        if not exists:
            db.add(SystemSetting(
                key=item["key"], value=item["value"],
                value_type=item["value_type"], setting_group=item["setting_group"],
                label=item["label"], description=item.get("description"),
                is_public=item.get("is_public", False),
                is_readonly=item.get("is_readonly", False),
                display_order=item.get("display_order", 0),
            ))
    await db.commit()