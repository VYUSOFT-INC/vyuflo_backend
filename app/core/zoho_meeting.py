# app/core/zoho_meeting.py
#
# Thin client for the Zoho Meeting API. Reuses the SAME OAuth credentials
# already used by app/core/zoho_client.py (Zoho Analytics) — same Zoho
# account, different product/API.

from __future__ import annotations

import time
import httpx
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings

# ── In-memory access-token cache ────────────────────────────────────────────
_access_token: Optional[str] = None
_access_token_expires_at: float = 0.0


async def _get_access_token() -> str:
    """Fetch a fresh access token using the refresh token. Cached ~55 min."""
    global _access_token, _access_token_expires_at
    if _access_token and time.time() < _access_token_expires_at - 60:
        return _access_token

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{settings.ZOHO_ACCOUNTS_BASE}/oauth/v2/token",
            params={
                "refresh_token": settings.ZOHO_REFRESH_TOKEN,
                "client_id":     settings.ZOHO_CLIENT_ID,
                "client_secret": settings.ZOHO_CLIENT_SECRET,
                "grant_type":    "refresh_token",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        _access_token = data["access_token"]
        _access_token_expires_at = time.time() + int(data.get("expires_in", 3600))
        return _access_token


async def create_meeting(
    *,
    topic:            str,
    start_time_utc:   datetime,
    duration_minutes: int,
    presenter_email:  str,          # attorney's email
    attendee_emails:  list[str],    # [employee_email] — HR is NOT added here
    agenda:           Optional[str] = None,
) -> dict:
    """Schedules a Zoho Meeting session and returns the raw API response."""
    token = await _get_access_token()
    start_iso = start_time_utc.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    payload = {
        "session": {
            "topic":            topic,
            "agenda":           agenda or topic,
            "startTime":        start_iso,
            "duration":         duration_minutes,
            "timezone":         "UTC",
            "presenter":        {"email": presenter_email},
            "attendees":        [{"email": e} for e in attendee_emails if e],
            "sendEmailInvite":  False,
            "waitingRoom":      False,
            "recordAutomatic":  False,
        }
    }

    url = f"{settings.ZOHO_MEETING_BASE}/api/v2/{settings.ZOHO_ORG_ID}/sessions.json"
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            url,
            headers={
                "Authorization": f"Zoho-oauthtoken {token}",
                "Content-Type":  "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()


async def delete_meeting(session_key: str) -> None:
    """Cancels a scheduled meeting. Silent on 404."""
    token = await _get_access_token()
    url = f"{settings.ZOHO_MEETING_BASE}/api/v2/{settings.ZOHO_ORG_ID}/sessions/{session_key}.json"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.delete(
            url,
            headers={"Authorization": f"Zoho-oauthtoken {token}"},
        )
        if resp.status_code not in (200, 204, 404):
            resp.raise_for_status()