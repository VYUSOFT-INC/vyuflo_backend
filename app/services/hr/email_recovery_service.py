# app/services/hr/email_recovery_service.py
#
# Handles the "your org removed access to this email" scenario:
# - When HR deactivates someone whose PRIMARY email is their org's work
#   email, flip User.email_is_active = False. Nothing else changes — they
#   can still log in (password stays valid), the frontend just shows a
#   banner driven by that flag telling them to update their primary email.
# - Two self-service functions let them do that update themselves once
#   logged in, OTP-verifying the new email before it's trusted.
#
# No new table: reuses UserOTP (same as the rest of the app) for verifying
# the new email, and Redis briefly holds which new email is pending between
# the "request" and "confirm" calls.

import secrets
import string
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.email import send_email
from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.redis import redis_delete, redis_get, redis_set
from app.models.visamodels import EmployerEmployee, User, UserOTP
from app.services.employee.services import db_create, db_update

OTP_EXPIRY_MINUTES = 10
REDIS_PENDING_EMAIL_PREFIX = "primary_email_change:"


def _generate_otp() -> str:
    return ''.join(secrets.choice(string.digits) for _ in range(6))


async def _email_taken_by_someone_else(db: AsyncSession, email: str, exclude_user_id) -> bool:
    """Same dedup rule as the invite flow: check both primary and linked_emails."""
    email = email.lower().strip()
    result = await db.execute(
        select(User).where(
            (User.email == email) | (User.linked_emails.any(email))
        )
    )
    existing = result.scalars().first()
    return bool(existing and existing.id != exclude_user_id)


# =============================================================================
# REACTIVE: mark the flag when HR removes someone's org access
# =============================================================================

async def flag_email_inactive_if_org_owned(db: AsyncSession, user: User) -> None:
    """
    Called from deactivate_employee(). Only flips the flag if the user's
    PRIMARY email IS the org email being removed — if they already use a
    different personal primary, nothing needs to happen.
    """
    result = await db.execute(
        select(EmployerEmployee).where(
            EmployerEmployee.employee_id == user.id,
            EmployerEmployee.work_email  == user.email,
        )
    )
    if result.scalars().first():
        await db_update(db, User, user.id, {"email_is_active": False})


# =============================================================================
# SELF-SERVICE: change my primary email (authenticated — via phone or
# whatever still-working credential got them logged in)
# =============================================================================

async def request_primary_email_change(db: AsyncSession, user: User, new_email: str) -> dict:
    """Step 1 — send an OTP to the candidate new email to prove they control it."""
    new_email = new_email.lower().strip()

    if await _email_taken_by_someone_else(db, new_email, user.id):
        raise ConflictException("This email is already used by another account.")

    otp = _generate_otp()
    await db_create(db, UserOTP(
        user_id     = user.id,
        otp_code    = otp,
        otp_type    = "email_verification",   # reuses the existing enum value
        expires_at  = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES),
        created_by  = user.id,
    ))

    # Hold the candidate email briefly — same TTL as the OTP itself
    await redis_set(
        f"{REDIS_PENDING_EMAIL_PREFIX}{user.id}",
        new_email,
        OTP_EXPIRY_MINUTES * 60,
    )

    await send_email(
        new_email,
        "Confirm your new email",
        f"Your verification code is: {otp}\n\nThis code expires in {OTP_EXPIRY_MINUTES} minutes.",
    )
    return {"message": "A verification code has been sent to your new email."}


async def confirm_primary_email_change(db: AsyncSession, user: User, otp_code: str) -> dict:
    """Step 2 — verify the OTP, swap User.email, move the old one into linked_emails,
    and clear the email_is_active flag (they're no longer at risk)."""
    stmt = (
        select(UserOTP)
        .where(
            UserOTP.user_id  == user.id,
            UserOTP.otp_type == "email_verification",
            UserOTP.is_used  == False,
        )
        .order_by(UserOTP.created_at.desc())
    )
    otp_row = await db.scalar(stmt)

    if not otp_row or otp_row.otp_code != otp_code:
        raise UnauthorizedException("Invalid or expired code")
    if otp_row.expires_at < datetime.now(timezone.utc):
        raise UnauthorizedException("Invalid or expired code")

    new_email = await redis_get(f"{REDIS_PENDING_EMAIL_PREFIX}{user.id}")
    if not new_email:
        raise ValueError("Verification expired — please request a new code.")

    # Guard against a race since the OTP was sent
    if await _email_taken_by_someone_else(db, new_email, user.id):
        raise ConflictException("This email is already used by another account.")

    await db_update(db, UserOTP, otp_row.id, {"is_used": True})

    old_email = user.email
    linked = list(user.linked_emails or [])
    if old_email not in linked:
        linked.append(old_email)

    await db_update(db, User, user.id, {
        "email":           new_email,
        "linked_emails":   linked,
        "email_is_active": True,   # clears the banner
    })
    await redis_delete(f"{REDIS_PENDING_EMAIL_PREFIX}{user.id}")

    return {"message": "Your primary email has been updated.", "new_primary_email": new_email}