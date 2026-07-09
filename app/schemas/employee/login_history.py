# src/app/schemas/login_history.py
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class LoginHistoryResponse(BaseModel):
    id:                 uuid.UUID
    user_id:            uuid.UUID
    status:             str        # "success" | "failed" | "blocked"
    auth_method:        str        # "email_password" | "google" | etc
    ip_address:         Optional[str]
    city:               Optional[str]
    country:            Optional[str]
    browser:            Optional[str]
    os:                 Optional[str]
    device_type:        str        # "desktop" | "mobile" | "tablet" | "unknown"
    failure_reason:     Optional[str]
    failed_attempts:    int
    is_suspicious:      bool
    is_current_session: bool
    logged_out_at:      Optional[datetime]
    created_at:         datetime

    model_config = {"from_attributes": True}


class LoginHistoryMarkSuspicious(BaseModel):
    is_suspicious: bool = True


class LoginHistoryListResponse(BaseModel):
    items: list[LoginHistoryResponse]
    total: int