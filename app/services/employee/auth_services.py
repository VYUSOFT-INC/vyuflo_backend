"""
Authentication service functions.
PRODUCTION VERSION — per-session refresh tokens, instant revocation via token_version,
refresh-token reuse detection, security alert notifications, personal-email fallback login.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from jose import JWTError
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import OTP_EXPIRE_SECONDS
from app.core.email import send_email
from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.redis import redis_delete, redis_get, redis_set, redis_scan_keys, redis_delete_many
from app.core.security import (
    create_access_token,
    create_refresh_token,
    new_session_id,
    decode_token,
    generate_otp,
    hash_otp,
    hash_password,
    verify_password,
)
from app.models.visamodels import (
    EmployerEmployee,
    PasswordResetToken,
    Role,
    User,
    UserEmail,
    UserLoginHistory,
    UserOTP,
    UserProfile,
    UserRole,
)
from app.schemas.employee.auth import ResetTokenStatus, UserRoleName
from app.services.employee.device_parser import parse_device
from app.services.employee.geolocation import get_ip_location
from app.services.employee.notification_service import (
    fire_new_device_login,
    fire_failed_login_alert,
    fire_password_changed,
    fire_unusual_activity,
)
from app.services.employee.otp_service import send_email_verification_otp
from app.services.employee.services import (
    _store_refresh_token,
    _verify_provider_token,
    db_create,
    db_get_by_field,
    db_get_by_id,
    db_update,
    get_user_profile,
    get_user_role,
    utc_now,
)
from app.core.config import settings
from app.services.employee.storage import resolve_url
from app.services.employee.user_profile_service import get_avatar_display_url


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                       LOGIN IDENTITY RESOLUTION                          ║
# ╚══════════════════════════════════════════════════════════════════════════╝

async def _find_user_by_login_identifier(db: AsyncSession, email: str) -> Optional[User]:
    """
    Resolves a login email to a User, checking three sources in order:

      1. user_emails — ANY verified email on file for the account, not
         just the original signup one. This is what makes "both emails
         work for login" possible: a person can add a personal email
         alongside their work email, verify it, and log in with either
         one going forward — neither replaces the other. Replaces the old
         approach of checking only User.email directly.

      2. EmployerEmployee.work_email — an org-issued login email, valid
         only while that membership is still active OR still inside its
         grace period (access_revoked_at is null or in the future). Kept
         as a fallback for org-issued emails that were never separately
         added to user_emails (shouldn't normally happen post-signup,
         but covers older/edge-case rows).
    """
    normalized = email.lower().strip()

    # ── 1. Any verified email on file (covers work + personal + signup) ─────
    result = await db.execute(
        select(User)
        .join(UserEmail, UserEmail.user_id == User.id)
        .where(UserEmail.email == normalized, UserEmail.is_verified == True)
    )
    user = result.scalar_one_or_none()
    if user:
        return user

    # ── 2. Active (or in-grace-period) org-issued work email ────────────────
    result = await db.execute(
        select(User)
        .join(EmployerEmployee, EmployerEmployee.employee_id == User.id)
        .where(
            EmployerEmployee.work_email == normalized,
            or_(
                EmployerEmployee.access_revoked_at.is_(None),
                EmployerEmployee.access_revoked_at > utc_now(),
            ),
        )
    )
    return result.scalar_one_or_none()


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                       SIGNUP                                             ║
# ╚══════════════════════════════════════════════════════════════════════════╝

async def service_signup(
    db: AsyncSession,
    *,
    first_name:        str,
    last_name:         str,
    email:             str,
    password:          str,
    role:              UserRoleName,
    phone:             Optional[str] = None,
    country_code:      Optional[str] = None,
    terms_accepted:    bool,
    marketing_opt_in:  bool          = False,
    newsletter_opt_in: bool          = False,
    referral_source:   Optional[str] = None,
) -> dict:
    """
    Step 1 of signup — creates User + minimal UserProfile + assigns role.
    Does NOT mark email as verified. Sends OTP verification email.
    """

    email = email.strip().lower()
    existing = await db.scalar(select(User).where(User.email == email))
    if existing:
        raise ConflictException("An account with this email already exists")

    user = User(
        first_name        = first_name,
        last_name         = last_name,
        email             = email,
        password_hash     = hash_password(password),
        phone             = phone,
        country_code      = country_code,
        auth_provider     = "email",
        is_active         = True,
        is_verified       = False,
        terms_accepted    = terms_accepted,
        terms_accepted_at = utc_now() if terms_accepted else None,
        marketing_opt_in  = marketing_opt_in,
        newsletter_opt_in = newsletter_opt_in,
        referral_source   = referral_source,
    )
    user = await db_create(db, user)

    profile = UserProfile(
        user_id         = user.id,
        onboarding_step = 1,
        full_legal_name = f"{first_name} {last_name}",
        created_by      = user.id,
        modified_by     = user.id,
        phone_number    = user.phone,
        country_code    = user.country_code,
    )
    await db_create(db, profile)

    role_obj = await db.scalar(select(Role).where(Role.name == role))
    if not role_obj:
        raise Exception("RBAC not seeded. Run seed migration first.")

    await db_create(db, UserRole(
        user_id     = user.id,
        role_id     = role_obj.id,
        assigned_by = user.id,
        created_by  = user.id,
        modified_by = user.id,
    ))

    # NEW — every account gets its first row in user_emails, marked verified
    # immediately (the password itself is the proof of ownership here —
    # unlike the "add a personal email" flow later, which has no password
    # check and requires an email-click confirmation instead).
    await db_create(db, UserEmail(
        user_id=user.id, email=email, is_verified=True, is_primary=True, source="signup",
    ))

    await send_email_verification_otp(db, user)

    roles      = [role_obj.name]
    session_id = new_session_id()
    access_token  = create_access_token(str(user.id), roles, user.email, user.first_name or "", user.last_name or "", user.token_version)
    refresh_token = create_refresh_token(str(user.id), session_id)

    await _store_refresh_token(str(user.id), session_id, refresh_token)
    profile_picture = getattr(profile, "profile_picture_url", None)
    theme_color = getattr(profile, "theme_color", None)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "roles": roles,
        "profile_picture": profile_picture,
        "theme_color": theme_color,
        "onboarding_step": profile.onboarding_step,
        "user": {
            "id":user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone": user.phone,
        },
    }


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                       LOGIN                                              ║
# ╚══════════════════════════════════════════════════════════════════════════╝

async def service_login(
    db: AsyncSession,
    *,
    email:      str,
    password:   str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> dict:

    # ── Resolve user by personal email OR active/grace-period work email ────
    user = await _find_user_by_login_identifier(db, email)

    if not user or not user.password_hash:
        raise UnauthorizedException("Invalid email or password")

    if not verify_password(password, user.password_hash):
        device_info = parse_device(user_agent)
        location = await get_ip_location(ip_address)
        await db_create(db, UserLoginHistory(
            user_id=user.id, status="failed", auth_method="email_password",
            ip_address=ip_address, user_agent=user_agent,
            browser=device_info["browser"], os=device_info["os"], device_type=device_info["device_type"],
            city=location["city"], country=location["country"],
            failure_reason="Incorrect password",
        ))

        recent_failures = (await db.execute(
            select(func.count(UserLoginHistory.id)).where(
                UserLoginHistory.user_id == user.id,
                UserLoginHistory.status == "failed",
                UserLoginHistory.created_at >= utc_now() - timedelta(minutes=15),
            )
        )).scalar_one()

        if recent_failures >= 3:
            await fire_failed_login_alert(db, user_id=user.id, ip_address=ip_address, attempt_count=recent_failures)

        raise UnauthorizedException("Invalid email or password")

    if not user.is_active:
        device_info = parse_device(user_agent)
        location = await get_ip_location(ip_address)
        await db_create(db, UserLoginHistory(
            user_id=user.id, status="blocked", auth_method="email_password",
            ip_address=ip_address, user_agent=user_agent,
            browser=device_info["browser"], os=device_info["os"], device_type=device_info["device_type"],
            city=location["city"], country=location["country"],
            failure_reason="Account suspended",
        ))
        raise UnauthorizedException("Your account has been suspended")

    roles        = await get_user_role(db, user.id)
    user_profile = await get_user_profile(db, user.id)

    device_info = parse_device(user_agent)
    location    = await get_ip_location(ip_address)

    await db_update(db, User, user.id, {"last_login_at": utc_now()})

    # ── 1. Gather signals BEFORE writing this login's own history row ───────
    # (so "seen_before" and "unusual" compare against PAST logins only)
    seen_before = (await db.execute(
        select(UserLoginHistory.id).where(
            UserLoginHistory.user_id == user.id,
            UserLoginHistory.status == "success",
            UserLoginHistory.browser == device_info["browser"],
            UserLoginHistory.os == device_info["os"],
        ).limit(1)
    )).scalar_one_or_none()

    recent_failures = (await db.execute(
        select(func.count(UserLoginHistory.id)).where(
            UserLoginHistory.user_id == user.id,
            UserLoginHistory.status == "failed",
            UserLoginHistory.created_at >= utc_now() - timedelta(minutes=15),
        )
    )).scalar_one()

    # reputation = await check_ip_reputation(ip_address)
    unusual    = await _is_unusual_location(db, user.id, location["country"])
    risk_score = _calculate_risk_score(
        unusual=unusual,
        # is_vpn=reputation["is_vpn"],
        is_new_device=(seen_before is None),
        recent_failures=recent_failures,
    )

    # ── 2. High risk → block outright (write the row first so it's on record) ─
    if risk_score >= 70:
        await db_create(db, UserLoginHistory(
            user_id=user.id, status="blocked", auth_method="email_password",
            ip_address=ip_address, user_agent=user_agent,
            browser=device_info["browser"], os=device_info["os"], device_type=device_info["device_type"],
            city=location["city"], country=location["country"],
            latitude=location["lat"], longitude=location["lon"],
            # is_vpn=reputation["is_vpn"], is_unusual=unusual, risk_score=risk_score,
            failure_reason="High-risk login blocked",
        ))
        await db.commit()
        risk_reasons = []
        if unusual: risk_reasons.append("sign-in from a new location")
        # if reputation["is_vpn"]: risk_reasons.append("VPN/proxy usage")
        if seen_before is None: risk_reasons.append("an unrecognized device")
        reason_str = " and ".join(risk_reasons) or "unusual account activity"

        await fire_unusual_activity(
            db, user_id=user.id,
            description=f"A login attempt was blocked due to {reason_str}.",
            ip_address=ip_address,
            location=", ".join(filter(None, [location["city"], location["country"]])) or "Unknown location",
        )
        await db.commit()
        raise UnauthorizedException(
            "This login was blocked for your security due to unusual activity. "
            "Please reset your password or contact support."
        )

    # ── 3. Record the successful login WITH the new risk fields ─────────────
    await db_create(db, UserLoginHistory(
        user_id=user.id, status="success", auth_method="email_password",
        ip_address=ip_address, user_agent=user_agent,
        browser=device_info["browser"], os=device_info["os"], device_type=device_info["device_type"],
        city=location["city"], country=location["country"],
        latitude=location["lat"], longitude=location["lon"],
        # is_vpn=reputation["is_vpn"], is_unusual=unusual, risk_score=risk_score,
    ))

    # ── 4. Medium risk OR new device → alert once, not twice ────────────────
    if risk_score >= 40 or seen_before is None:
        await fire_new_device_login(
            db, user_id=user.id, ip_address=ip_address,
            city=location["city"], country=location["country"],
            browser=device_info["browser"], os_name=device_info["os"], device_type=device_info["device_type"],
        )

    session_id    = new_session_id()
    access_token  = create_access_token(str(user.id), roles, user.email, user.first_name or "", user.last_name or "", user.token_version)
    refresh_token = create_refresh_token(str(user.id), session_id)
    await _store_refresh_token(str(user.id), session_id, refresh_token)
    return {
        "access_token":    access_token,
        "refresh_token":   refresh_token,
        "roles":           roles,
        "profile_picture": get_avatar_display_url(user_profile) if user_profile else None,
        "theme_color": user_profile.theme_color if user_profile else None,
        "tour_employee_seen": user_profile.tour_employee_seen  if user_profile else False,
        "tour_hr_seen":       user_profile.tour_hr_seen        if user_profile else False,
        "tour_attorney_seen": user_profile.tour_attorney_seen  if user_profile else False,
        "tour_admin_seen":    user_profile.tour_admin_seen     if user_profile else False,
        "user": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name":  user.last_name,
            "email":      user.email,
            "phone":      user.phone,
        },
    }
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                       SSO LOGIN                                          ║
# ╚══════════════════════════════════════════════════════════════════════════╝

async def service_sso_login(
    db: AsyncSession,
    *,
    provider:       str,
    provider_token: str,
    terms_accepted: bool,
    ip_address:     str | None,
) -> dict:
    provider = provider.lower()

    if provider == "google":
        user_info = await _verify_google_token(provider_token)
    elif provider == "microsoft":
        user_info = await _verify_microsoft_token(provider_token)
    elif provider == "linkedin":
        user_info = await _exchange_linkedin_code(provider_token)
    else:
        raise ValueError(f"Unsupported SSO provider: {provider}")

    email      = user_info["email"].strip().lower()
    first_name = user_info["first_name"]
    last_name  = user_info["last_name"]

    user = await db_get_by_field(db, User, "email", email)

    if not user:
        user = User(
            first_name        = first_name,
            last_name         = last_name,
            email             = email,
            password_hash     = None,
            auth_provider     = provider,
            is_active         = True,
            is_verified       = True,
            terms_accepted    = terms_accepted,
            terms_accepted_at = utc_now() if terms_accepted else None,
        )
        user = await db_create(db, user)

        profile = UserProfile(
            user_id         = user.id,
            onboarding_step = 1,
            full_legal_name = f"{first_name} {last_name}",
            created_by      = user.id,
            modified_by     = user.id,
        )
        await db_create(db, profile)

        role_obj = await db.scalar(select(Role).where(Role.name == "employee"))
        if not role_obj:
            raise Exception("RBAC not seeded. Run seed migration first.")
        await db_create(db, UserRole(
            user_id     = user.id,
            role_id     = role_obj.id,
            assigned_by = user.id,
            created_by  = user.id,
            modified_by = user.id,
        ))

        # NEW — same treatment as email/password signup: first user_emails
        # row, verified immediately (SSO providers already verify the
        # email themselves before handing it to us).
        await db_create(db, UserEmail(
            user_id=user.id, email=email, is_verified=True, is_primary=True, source="signup",
        ))
    else:
        if user.auth_provider == "email":
            await db_update(db, User, user.id, {"auth_provider": provider})

    roles        = await get_user_role(db, user.id)
    user_profile = await get_user_profile(db, user.id)

    session_id    = new_session_id()
    access_token  = create_access_token(str(user.id), roles, user.email, user.first_name, user.last_name, user.token_version)
    refresh_token = create_refresh_token(str(user.id), session_id)
    await _store_refresh_token(str(user.id), session_id, refresh_token)

    return {
        "access_token":    access_token,
        "refresh_token":   refresh_token,
        "roles":           roles,
        "profile_picture":    user_profile.profile_picture_url if user_profile else None,
        "theme_color":        user_profile.theme_color         if user_profile else None,
        "tour_employee_seen": user_profile.tour_employee_seen  if user_profile else False,
        "tour_hr_seen":       user_profile.tour_hr_seen        if user_profile else False,
        "tour_attorney_seen": user_profile.tour_attorney_seen  if user_profile else False,
        "tour_admin_seen":    user_profile.tour_admin_seen     if user_profile else False,
        "user": {
            "first_name": user.first_name,
            "last_name":  user.last_name,
            "email":      user.email,
            "phone":      user.phone,
        },
        "onboarding_step": 1,
    }


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                       TOKEN REFRESH                                      ║
# ╚══════════════════════════════════════════════════════════════════════════╝

async def service_refresh_token(db: AsyncSession, *, refresh_token: str) -> dict:
    """
    Exchange a valid refresh token for a new access + refresh token pair.
    Detects reuse of an already-rotated token (theft signal) and revokes
    that session immediately if detected.
    """
    try:
        payload    = decode_token(refresh_token)
        user_id    = payload.get("sub")
        session_id = payload.get("session_id")
        tok_type   = payload.get("type")
        if not user_id or not session_id or tok_type != "refresh":
            raise UnauthorizedException("Invalid refresh token")
    except JWTError:
        raise UnauthorizedException("Invalid or expired refresh token")

    key    = f"refresh:{user_id}:{session_id}"
    stored = await redis_get(key)

    if not stored:
        raise UnauthorizedException("Session expired. Please log in again.")

    if stored != refresh_token:
        # Reuse detected — token presented doesn't match the last-issued one
        # for this session. Rotation always overwrites Redis, so this means
        # an old, already-superseded token is being replayed — likely theft.
        await redis_delete(key)
        raise UnauthorizedException("Security alert: token reuse detected. Please log in again.")

    user = await db_get_by_id(db, User, uuid.UUID(user_id))
    if not user or not user.is_active:
        raise UnauthorizedException("User not found or inactive")

    roles = await get_user_role(db, user.id)

    new_access  = create_access_token(str(user.id), roles, user.email, user.first_name, user.last_name, user.token_version)
    new_refresh = create_refresh_token(str(user.id), session_id)
    await _store_refresh_token(str(user.id), session_id, new_refresh)

    return {"access_token": new_access, "refresh_token": new_refresh}


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                       LOGOUT                                             ║
# ╚══════════════════════════════════════════════════════════════════════════╝

async def service_logout(user_id: uuid.UUID, session_id: str) -> None:
    """Invalidate this one session's refresh token in Redis."""
    await redis_delete(f"refresh:{user_id}:{session_id}")


async def service_sign_out_all_devices(db: AsyncSession, user_id: uuid.UUID) -> int:
    """
    Deletes every refresh-token session for this user AND bumps token_version,
    so already-issued access tokens on every device die immediately too —
    not just future refresh attempts. Returns count of sessions revoked.
    """
    keys = await redis_scan_keys(f"refresh:{user_id}:*")
    await redis_delete_many(keys)

    user = await db_get_by_id(db, User, user_id)
    if user:
        await db_update(db, User, user.id, {"token_version": user.token_version + 1})

    return len(keys)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                  PERSONAL EMAIL — ADD + VERIFY                          ║
# ╚══════════════════════════════════════════════════════════════════════════╝

# async def service_add_personal_email(
#     db: AsyncSession,
#     *,
#     user_id: uuid.UUID,
#     personal_email: str,
# ) -> None:
#     """
#     Adds a personal/backup email as an ADDITIONAL login credential — does
#     NOT replace or touch the account's existing email(s). Creates an
#     unverified row in user_emails; it only becomes usable for login once
#     the OTP code is confirmed. This is what makes "both emails log in"
#     possible: the original signup/work email keeps working exactly as
#     before, and this new one becomes a second valid path in once
#     verified — neither one displaces the other.

#     Pure OTP, no magic link — sends a 6-digit code the person types back
#     into the app while still in their authenticated session. Matches the
#     existing-user merge flow's verification model for consistency, and
#     avoids a magic link's actual weak point: the "someone with access to
#     this inbox could click this link" argument only holds if the person
#     reading the email is a stranger — but the code and a would-be link
#     both live in the same message either way, so a single, explicit
#     "type the code back into the app" step is the simpler, single
#     mechanism to reason about instead of two overlapping ones.
#     """
#     personal_email = personal_email.strip().lower()

#     existing = await db.scalar(select(UserEmail).where(UserEmail.email == personal_email))
#     if existing:
#         raise ConflictException("This email is already in use by another account.")

#     code    = f"{secrets.randbelow(1_000_000):06d}"
#     expires = utc_now() + timedelta(minutes=15)

#     await db_create(db, UserEmail(
#         user_id=user_id, email=personal_email, is_verified=False, is_primary=False,
#         source="personal", verify_token=code, verify_token_expires=expires,
#     ))

#     await send_email(
#         to=personal_email,
#         subject="Verify your personal email — Vyuflo",
#         body=(
#             "You (or your organization) requested to add this email as a "
#             "backup login for your Vyuflo account.\n\n"
#             f"Your verification code: {code}\n\n"
#             "Enter this code in Vyuflo to confirm. It expires in 15 minutes. "
#             "If you didn't request this, ignore this email."
#         ),
#     )

async def service_add_personal_email(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    personal_email: str,
) -> None:
    personal_email = personal_email.strip().lower()

    existing = await db.scalar(select(UserEmail).where(UserEmail.email == personal_email))

    if existing:
        if existing.is_verified:
            # Genuinely taken — someone else already verified this email.
            raise ConflictException("This email is already in use by another account.")

        if existing.user_id == user_id:
            # Same person retrying (e.g. previous attempt was abandoned or the
            # code expired) — just refresh the code instead of blocking them.
            code = f"{secrets.randbelow(1_000_000):06d}"
            expires = utc_now() + timedelta(minutes=15)
            await db_update(db, UserEmail, existing.id, {
                "verify_token": code, "verify_token_expires": expires,
            })
            await send_email(
                to=personal_email,
                subject="Verify your personal email — Vyuflo",
                body=(
                    "You (or your organization) requested to add this email as a "
                    "backup login for your Vyuflo account.\n\n"
                    f"Your verification code: {code}\n\n"
                    "Enter this code in Vyuflo to confirm. It expires in 15 minutes. "
                    "If you didn't request this, ignore this email."
                ),
            )
            return

        # Unverified row exists but belongs to a DIFFERENT user_id — could be
        # a genuine race between two people adding the same email, or (far
        # more likely in practice) stale data from earlier testing. Since we
        # can't safely tell which, block but say something more accurate
        # than "in use by another account" when it isn't actually verified.
        raise ConflictException("This email is already pending verification elsewhere.")

    code    = f"{secrets.randbelow(1_000_000):06d}"
    expires = utc_now() + timedelta(minutes=15)

    await db_create(db, UserEmail(
        user_id=user_id, email=personal_email, is_verified=False, is_primary=False,
        source="personal", verify_token=code, verify_token_expires=expires,
    ))

    await send_email(
        to=personal_email,
        subject="Verify your personal email — Vyuflo",
        body=(
            "You (or your organization) requested to add this email as a "
            "backup login for your Vyuflo account.\n\n"
            f"Your verification code: {code}\n\n"
            "Enter this code in Vyuflo to confirm. It expires in 15 minutes. "
            "If you didn't request this, ignore this email."
        ),
    )


async def service_verify_personal_email_otp(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    otp_code: str,
) -> None:
    """
    Confirms the code from service_add_personal_email while the person is
    still in their authenticated session — no public token lookup, since
    unlike a magic link (which must work for someone clicking from an
    email client with no active session), this is entered directly in
    the app by someone we already know is logged in. Scoping the lookup
    to user_id also means a code can never be replayed against a
    different account by mistake or malice.
    """
    row = await db.scalar(
        select(UserEmail).where(
            UserEmail.user_id == user_id,
            UserEmail.verify_token == otp_code.strip(),
            UserEmail.is_verified == False,
        )
    )
    if not row:
        raise BadRequestException("Invalid verification code.")

    if not row.verify_token_expires or row.verify_token_expires < utc_now():
        raise BadRequestException("This code has expired. Please request a new one.")

    await db_update(db, UserEmail, row.id, {
        "is_verified": True, "verify_token": None, "verify_token_expires": None,
    })


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                       PASSWORD CHANGE / RESET                           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

async def service_change_password(
    db: AsyncSession, *, user_id: uuid.UUID, new_password: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    user = await db_get_by_id(db, User, user_id)
    if not user:
        raise NotFoundException("User not found")

    await db_update(db, User, user.id, {
        "password_hash": hash_password(new_password),
        "token_version": user.token_version + 1,
    })
    device_info = parse_device(user_agent)
    device_str = f"{device_info['browser']} on {device_info['os']}" if user_agent else None
    await fire_password_changed(db, user_id=user.id, ip_address=ip_address, device_str=device_str)


async def service_request_password_reset(
    db: AsyncSession, *, email: str
) -> PasswordResetToken:
    user = await db_get_by_field(db, User, "email", email.lower().strip())
    if not user:
        return None

    otp        = generate_otp(6)
    otp_hash   = hash_otp(otp)
    expires_at = utc_now() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

    token = PasswordResetToken(
        user_id         = user.id,
        requested_email = email,
        otp_code        = otp,
        otp_code_hash   = otp_hash,
        expires_at      = expires_at,
        status          = ResetTokenStatus.PENDING.value,
        resend_count    = 0,
        failed_attempts = 0,
    )
    token = await db_create(db, token)
    await redis_set(f"pwd_reset:{token.id}", otp, OTP_EXPIRE_SECONDS)

    token._plain_otp = otp
    return token


# async def service_verify_reset_otp(
#     db: AsyncSession,
#     *,
#     reset_token_id: str,
#     otp_code: str,
# ) -> PasswordResetToken:
#     token = await db_get_by_id(db, PasswordResetToken, uuid.UUID(reset_token_id))
#     if not token or token.status not in ("pending",):
#         raise BadRequestException("Invalid or expired reset request")

#     cached_otp = await redis_get(f"pwd_reset:{reset_token_id}")
#     if not cached_otp or cached_otp != otp_code:
#         raise BadRequestException("Invalid or expired OTP code")

#     token = await db_update(db, PasswordResetToken, token.id, {
#         "otp_verified":    True,
#         "otp_verified_at": utc_now(),
#         "status":          "verified",
#     })
#     await redis_delete(f"pwd_reset:{reset_token_id}")
#     return token

async def service_verify_reset_otp(
    db: AsyncSession,
    *,
    reset_token_id: str,
    otp_code: str,
) -> PasswordResetToken:
    token = await db_get_by_id(db, PasswordResetToken, uuid.UUID(reset_token_id))
    if not token or token.status not in ("pending",):
        raise BadRequestException("Invalid or expired reset request")

    if token.failed_attempts >= settings.OTP_MAX_ATTEMPTS:
        await db_update(db, PasswordResetToken, token.id, {"status": "locked"})
        raise BadRequestException("Too many incorrect attempts. Please request a new code.")

    cached_otp = await redis_get(f"pwd_reset:{reset_token_id}")
    if not cached_otp or cached_otp != otp_code:
        await db_update(db, PasswordResetToken, token.id, {"failed_attempts": token.failed_attempts + 1})
        raise BadRequestException("Invalid or expired OTP code")

    token = await db_update(db, PasswordResetToken, token.id, {
        "otp_verified":    True,
        "otp_verified_at": utc_now(),
        "status":          "verified",
    })
    await redis_delete(f"pwd_reset:{reset_token_id}")
    return token

async def service_complete_password_reset(
    db: AsyncSession, *, reset_token_id: str, new_password: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> User:
    token = await db_get_by_id(db, PasswordResetToken, uuid.UUID(reset_token_id))
    if not token or token.status != "verified":
        raise BadRequestException("OTP not verified or request expired")

    user = await db_get_by_id(db, User, token.user_id)
    if not user:
        raise NotFoundException("User not found")

    await db_update(db, User, user.id, {
        "password_hash": hash_password(new_password),
        "token_version": user.token_version + 1,
    })
    await db_update(db, PasswordResetToken, token.id, {
        "status": "completed",
        "password_reset_completed": True,
        "password_reset_completed_at": utc_now(),
    })

    device_info = parse_device(user_agent)
    device_str = f"{device_info['browser']} on {device_info['os']}" if user_agent else None
    await fire_password_changed(db, user_id=user.id, ip_address=ip_address, device_str=device_str)

    return user


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                  SSO PROVIDER HELPERS                                    ║
# ╚══════════════════════════════════════════════════════════════════════════╝

async def _verify_google_token(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if res.status_code != 200:
        raise ValueError("Invalid Google token")
    data = res.json()
    return {
        "email":       data["email"],
        "first_name":  data.get("given_name") or (data.get("name", "").split()[0] if data.get("name") else ""),
        "last_name":   data.get("family_name") or (" ".join(data.get("name", "").split()[1:]) if data.get("name") else ""),
        "provider_id": data["sub"],
    }


async def _verify_microsoft_token(id_token_str: str) -> dict:
    import base64, json
    try:
        payload_b64  = id_token_str.split(".")[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload      = json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception:
        raise ValueError("Invalid Microsoft token")

    email      = payload.get("email") or payload.get("preferred_username", "")
    full_name  = payload.get("name", "")
    name_parts = full_name.strip().split(" ", 1)
    first_name = payload.get("given_name")  or (name_parts[0] if name_parts else "")
    last_name  = payload.get("family_name") or (name_parts[1] if len(name_parts) > 1 else "")

    return {
        "email":       email.lower(),
        "first_name":  first_name,
        "last_name":   last_name,
        "provider_id": payload.get("oid") or payload.get("sub", ""),
    }


async def _exchange_linkedin_code(code: str) -> dict:
    import os
    client_id     = os.environ["LINKEDIN_CLIENT_ID"]
    client_secret = os.environ["LINKEDIN_CLIENT_SECRET"]
    redirect_uri  = os.environ["LINKEDIN_REDIRECT_URI"]

    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type":    "authorization_code",
                "code":          code,
                "redirect_uri":  redirect_uri,
                "client_id":     client_id,
                "client_secret": client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_res.status_code != 200:
            raise ValueError("LinkedIn token exchange failed")

        access_token = token_res.json()["access_token"]

        user_res = await client.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_res.status_code != 200:
            raise ValueError("LinkedIn userinfo fetch failed")
        data = user_res.json()

    first_name = data.get("given_name", "")
    last_name  = data.get("family_name", "")
    if not first_name:
        full       = data.get("name", "")
        parts      = full.strip().split(" ", 1)
        first_name = parts[0] if parts else ""
        last_name  = parts[1] if len(parts) > 1 else last_name

    return {
        "email":       data.get("email", "").lower(),
        "first_name":  first_name,
        "last_name":   last_name,
        "provider_id": data.get("sub", ""),
    }


async def _is_unusual_location(db: AsyncSession, user_id: uuid.UUID, country: str | None) -> bool:
    if not country:
        return False
    has_history = (await db.execute(
        select(UserLoginHistory.id).where(
            UserLoginHistory.user_id == user_id, UserLoginHistory.status == "success",
        ).limit(1)
    )).scalar_one_or_none() is not None
    seen_country = (await db.execute(
        select(UserLoginHistory.id).where(
            UserLoginHistory.user_id == user_id,
            UserLoginHistory.status == "success",
            UserLoginHistory.country == country,
        ).limit(1)
    )).scalar_one_or_none() is not None
    return has_history and not seen_country


def _calculate_risk_score(unusual: bool, is_new_device: bool, recent_failures: int) -> int:
    score = 0
    if unusual: score += 30
    # if is_vpn: score += 25
    if is_new_device: score += 20
    if recent_failures >= 2: score += 25
    return score