
# """
# Authentication service functions.
# PRODUCTION VERSION — all auth logic, cookie-ready responses.
# """
# from __future__ import annotations

# import uuid
# from datetime import datetime, timedelta, timezone
# from typing import Any, Optional

# import httpx
# from jose import jwt
# from sqlalchemy import select
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.core.constants import OTP_EXPIRE_SECONDS
# from app.core.exceptions import (
#     BadRequestException,
#     ConflictException,
#     NotFoundException,
#     UnauthorizedException,
# )
# from app.core.redis import redis_delete, redis_get, redis_set
# from app.core.security import (
#     create_access_token,
#     create_refresh_token,
#     generate_otp,
#     hash_otp,
#     hash_password,
#     verify_password,
# )
# from app.models.visamodels import (
#     PasswordResetToken,
#     Role,
#     User,
#     UserLoginHistory,
#     UserOTP,
#     UserProfile,
#     UserRole,
# )
# from app.schemas.employee.auth import ResetTokenStatus, UserRoleName
# from app.services.employee.device_parser import parse_device
# from app.services.employee.geolocation import get_ip_location
# from app.services.employee.otp_service import send_email_verification_otp
# from app.services.employee.services import (
#     _store_refresh_token,
#     _verify_provider_token,
#     db_create,
#     db_get_by_field,
#     db_get_by_id,
#     db_update,
#     get_user_profile,
#     get_user_role,
#     utc_now,
# )
# from app.core.config import settings
# from app.services.employee.storage import resolve_url


# # ╔══════════════════════════════════════════════════════════════════════════╗
# # ║                       SIGNUP                                             ║
# # ╚══════════════════════════════════════════════════════════════════════════╝

# async def service_signup(
#     db: AsyncSession,
#     *,
#     first_name:        str,
#     last_name:         str,
#     email:             str,
#     password:          str,
#     role:              UserRoleName,
#     phone:             Optional[str] = None,
#     country_code:      Optional[str] = None,
#     terms_accepted:    bool,
#     marketing_opt_in:  bool          = False,
#     newsletter_opt_in: bool          = False,
#     referral_source:   Optional[str] = None,
# ) -> dict:
#     """
#     Step 1 of signup — creates User + minimal UserProfile + assigns role.
#     Does NOT mark email as verified.
#     Sends OTP verification email.
#     Returns tokens + ui_data for the ui_session cookie.
#     """

#     # ── 1. Normalize & deduplicate ─────────────────────────────────────────
#     email = email.strip().lower()
#     existing = await db.scalar(select(User).where(User.email == email))
#     if existing:
#         raise ConflictException("An account with this email already exists")

#     # ── 2. Create User ─────────────────────────────────────────────────────
#     user = User(
#         first_name        = first_name,
#         last_name         = last_name,
#         email             = email,
#         password_hash     = hash_password(password),
#         phone             = phone,
#         country_code      = country_code,
#         auth_provider     = "email",
#         is_active         = True,
#         is_verified       = False,
#         terms_accepted    = terms_accepted,
#         terms_accepted_at = utc_now() if terms_accepted else None,
#         marketing_opt_in  = marketing_opt_in,
#         newsletter_opt_in = newsletter_opt_in,
#         referral_source   = referral_source,
#     )
#     user = await db_create(db, user)

#     # ── 3. Create minimal UserProfile ──────────────────────────────────────
#     profile = UserProfile(
#         user_id         = user.id,
#         onboarding_step = 1,
#         full_legal_name = f"{first_name} {last_name}",
#         created_by      = user.id,
#         modified_by     = user.id,
#         phone_number    = user.phone,
#         country_code    = user.country_code,
#     )
#     await db_create(db, profile)

#     # ── 4. Assign role ─────────────────────────────────────────────────────
#     role_obj = await db.scalar(select(Role).where(Role.name == role))
#     if not role_obj:
#         raise Exception("RBAC not seeded. Run seed migration first.")

#     await db_create(db, UserRole(
#         user_id     = user.id,
#         role_id     = role_obj.id,
#         assigned_by = user.id,
#         created_by  = user.id,
#         modified_by = user.id,
#     ))
 
#     # ── 5. Send email verification OTP ─────────────────────────────────────
#     await send_email_verification_otp(db, user)

#     # ── 6. Generate tokens ─────────────────────────────────────────────────
#     roles         = [role_obj.name]
#     access_token = create_access_token(str(user.id),roles,user.email,user.first_name or "",user.last_name or "")
#     refresh_token = create_refresh_token(str(user.id))

#     await _store_refresh_token(str(user.id), refresh_token)
    
#     profile_picture = getattr(profile, "profile_picture_url", None)
#     theme_color = getattr(profile, "theme_color", None)
#     return {
#         "access_token": access_token,
#         "refresh_token": refresh_token,
#         "roles": roles,
#         "profile_picture": profile_picture,
#         "theme_color": theme_color,
#         "onboarding_step": profile.onboarding_step,
#         "user": {
#             "first_name": user.first_name,
#             "last_name": user.last_name,
#             "email": user.email,
#             "phone": user.phone,
#         },
#     }


# # ╔══════════════════════════════════════════════════════════════════════════╗
# # ║                       LOGIN                                              ║
# # ╚══════════════════════════════════════════════════════════════════════════╝
# async def service_login(
#     db: AsyncSession,
#     *,
#     email:      str,
#     password:   str,
#     ip_address: Optional[str] = None,
#     user_agent: Optional[str] = None,
# ) -> dict:

#     user = await db_get_by_field(db, User, "email", email.lower().strip())

#     if not user or not user.password_hash:
#         raise UnauthorizedException("Invalid email or password")

#     if not verify_password(password, user.password_hash):
#         device_info = parse_device(user_agent)
#         location = await get_ip_location(ip_address)
#         await db_create(db, UserLoginHistory(
#             user_id        = user.id,
#             status         = "failed",
#             auth_method    = "email_password",
#             ip_address     = ip_address,
#             user_agent     = user_agent,
#             browser        = device_info["browser"],
#             os             = device_info["os"],
#             device_type    = device_info["device_type"],
#             city           = location["city"],
#             country        = location["country"],
#             failure_reason = "Incorrect password",
#         ))
#         raise UnauthorizedException("Invalid email or password")

#     if not user.is_active:
#         device_info = parse_device(user_agent)
#         location = await get_ip_location(ip_address)
#         await db_create(db, UserLoginHistory(
#             user_id        = user.id,
#             status         = "blocked",
#             auth_method    = "email_password",
#             ip_address     = ip_address,
#             user_agent     = user_agent,
#             browser        = device_info["browser"],
#             os             = device_info["os"],
#             device_type    = device_info["device_type"],
#             city           = location["city"],
#             country        = location["country"],
#             failure_reason = "Account suspended",
#         ))
#         raise UnauthorizedException("Your account has been suspended")

#     # ── Roles & profile ────────────────────────────────────────────────────
#     roles        = await get_user_role(db, user.id)
#     user_profile = await get_user_profile(db, user.id)

#     # ── Record successful login (with device + location) ──────────────────
#     device_info = parse_device(user_agent)
#     location    = await get_ip_location(ip_address)

#     await db_update(db, User, user.id, {"last_login_at": utc_now()})
#     await db_create(db, UserLoginHistory(
#         user_id     = user.id,
#         status      = "success",
#         auth_method = "email_password",
#         ip_address  = ip_address,
#         user_agent  = user_agent,
#         browser     = device_info["browser"],
#         os          = device_info["os"],
#         device_type = device_info["device_type"],
#         city        = location["city"],
#         country     = location["country"],
#     ))

#     # ── Tokens ────────────────────────────────────────────────────────────
#     access_token = create_access_token(str(user.id), roles, user.email, user.first_name or "", user.last_name or "")
#     refresh_token = create_refresh_token(str(user.id))
#     await _store_refresh_token(str(user.id), refresh_token)
#     return {
#         "access_token":    access_token,
#         "refresh_token":   refresh_token,
#         "roles":           roles,
#         "profile_picture": await resolve_url(user_profile.profile_picture_url) if user_profile else None,
#         "theme_color": user_profile.theme_color if user_profile else None,
#         "tour_employee_seen": user_profile.tour_employee_seen  if user_profile else False,
#         "tour_hr_seen":       user_profile.tour_hr_seen        if user_profile else False,
#         "tour_attorney_seen": user_profile.tour_attorney_seen  if user_profile else False,
#         "tour_admin_seen":    user_profile.tour_admin_seen     if user_profile else False,
#         "user": {
#             "id":user.id,
#             "first_name": user.first_name,
#             "last_name":  user.last_name,
#             "email":      user.email,
#             "phone":      user.phone,
#         },
#     }




# # async def service_login(
# #     db: AsyncSession,
# #     *,
# #     email:      str,
# #     password:   str,
# #     ip_address: Optional[str] = None,
# #     user_agent: Optional[str] = None,
# # ) -> dict:

# #     # ── Fetch & validate user ──────────────────────────────────────────────
# #     user = await db_get_by_field(db, User, "email", email.lower().strip())

# #     if not user or not user.password_hash:
# #         raise UnauthorizedException("Invalid email or password")

# #     if not verify_password(password, user.password_hash):
# #         await db_create(db, UserLoginHistory(
# #             user_id        = user.id,
# #             status         = "failed",
# #             auth_method    = "email_password",
# #             ip_address     = ip_address,
# #             failure_reason = "Incorrect password",
# #         ))
# #         raise UnauthorizedException("Invalid email or password")

# #     if not user.is_active:
# #         await db_create(db, UserLoginHistory(
# #             user_id        = user.id,
# #             status         = "blocked",
# #             auth_method    = "email_password",
# #             ip_address     = ip_address,
# #             failure_reason = "Account suspended",
# #         ))
# #         raise UnauthorizedException("Your account has been suspended")

# #     # ── Roles & profile ────────────────────────────────────────────────────
# #     roles        = await get_user_role(db, user.id)
# #     user_profile = await get_user_profile(db, user.id)

# #     # ── Record successful login ────────────────────────────────────────────
# #     await db_update(db, User, user.id, {"last_login_at": utc_now()})
# #     await db_create(db, UserLoginHistory(
# #         user_id     = user.id,
# #         status      = "success",
# #         auth_method = "email_password",
# #         ip_address  = ip_address,
# #     ))

# #     # ── Tokens ────────────────────────────────────────────────────────────
# #     access_token = create_access_token(str(user.id),roles,user.email,user.first_name or "",user.last_name or "",)
# #     refresh_token = create_refresh_token(str(user.id))
# #     await _store_refresh_token(str(user.id), refresh_token)
# #     return {
# #         "access_token":    access_token,
# #         "refresh_token":   refresh_token,
# #         "roles":           roles,
# #         "profile_picture": await resolve_url(user_profile.profile_picture_url) if user_profile else None,
# #         "theme_color": user_profile.theme_color if user_profile else None,
# #         "tour_employee_seen": user_profile.tour_employee_seen  if user_profile else False,
# #         "tour_hr_seen":       user_profile.tour_hr_seen        if user_profile else False,
# #         "tour_attorney_seen": user_profile.tour_attorney_seen  if user_profile else False,
# #         "tour_admin_seen":    user_profile.tour_admin_seen     if user_profile else False,
# #         "user": {
# #             "id":user.id,
# #             "first_name": user.first_name,
# #             "last_name":  user.last_name,
# #             "email":      user.email,
# #             "phone":      user.phone,
# #         },
# #     }

# #login phone

# def _looks_like_email(identifier: str) -> bool:
#     return "@" in identifier


# # async def _get_user_by_identifier(db: AsyncSession, identifier: str, channel: str) -> Optional[User]:
# #     if channel == "email":
# #         return await db_get_by_field(db, User, "email", identifier.lower())
# #     return await db_get_by_field(db, User, "phone", identifier)


# # async def service_request_login_otp(db: AsyncSession, *, identifier: str) -> dict:
# #     """
# #     Step 1 of passwordless login.
# #     `identifier` is either an email address or a phone number — auto-detected.

# #     Always returns a generic success message (no user enumeration), but only
# #     actually generates + sends an OTP if a matching, active account exists.
# #     """
# #     identifier = identifier.strip()
# #     channel = "email" if _looks_like_email(identifier) else "phone"

# #     user = await _get_user_by_identifier(db, identifier, channel)

# #     if user and user.is_active:
# #         if channel == "phone" and not user.phone:
# #             pass  # no phone on file — silently skip, same as "not found"
# #         else:
# #             await send_login_otp(db, user, channel)

# #     return {
# #         "message": f"If an account exists for that {channel}, a login code has been sent.",
# #         "channel": channel,
# #     }


# # async def service_verify_login_otp(
# #     db: AsyncSession,
# #     *,
# #     identifier: str,
# #     otp_code: str,
# #     ip_address: Optional[str] = None,
# #     user_agent: Optional[str] = None,
# # ) -> dict:
# #     """
# #     Step 2 of passwordless login — verifies the OTP and issues tokens.
# #     """
# #     identifier = identifier.strip()
# #     channel = "email" if _looks_like_email(identifier) else "phone"

# #     user = await _get_user_by_identifier(db, identifier, channel)
# #     if not user:
# #         raise UnauthorizedException("Invalid or expired code")

# #     # ── Fetch most recent unused login OTP for this user ────────────────────
# #     stmt = (
# #         select(UserOTP)
# #         .where(
# #             UserOTP.user_id == user.id,
# #             UserOTP.otp_type == "two_factor_auth",
# #             UserOTP.is_used == False,
# #         )
# #         .order_by(UserOTP.created_at.desc())
# #     )
# #     otp_row = await db.scalar(stmt)

# #     if not otp_row or otp_row.otp_code != otp_code:
# #         raise UnauthorizedException("Invalid or expired code")

# #     if otp_row.expires_at < utc_now():
# #         raise UnauthorizedException("Invalid or expired code")

# #     if not user.is_active:
# #         raise UnauthorizedException("Your account has been suspended")

# #     # ── Mark OTP as used (single use) ───────────────────────────────────────
# #     await db_update(db, UserOTP, otp_row.id, {"is_used": True})

# #     # ── Roles & profile ──────────────────────────────────────────────────────
# #     roles        = await get_user_role(db, user.id)
# #     user_profile = await get_user_profile(db, user.id)

# #     # ── Record successful login ─────────────────────────────────────────────
# #     await db_update(db, User, user.id, {"last_login_at": utc_now()})
# #     await db_create(db, UserLoginHistory(
# #         user_id     = user.id,
# #         status      = "success",
# #         auth_method = "otp",
# #         ip_address  = ip_address,
# #     ))

# #     # ── Tokens ────────────────────────────────────────────────────────────
# #     access_token  = create_access_token(str(user.id), roles, user.email, user.first_name or "", user.last_name or "")
# #     refresh_token = create_refresh_token(str(user.id))
# #     await _store_refresh_token(str(user.id), refresh_token)

# #     return {
# #         "access_token":    access_token,
# #         "refresh_token":   refresh_token,
# #         "roles":           roles,
# #         "profile_picture": user_profile.profile_picture_url if user_profile else None,
# #         "theme_color":     user_profile.theme_color if user_profile else None,
# #         "user": {
# #             "id":         user.id,
# #             "first_name": user.first_name,
# #             "last_name":  user.last_name,
# #             "email":      user.email,
# #             "phone":      user.phone,
# #         },
# #     }

# # ╔══════════════════════════════════════════════════════════════════════════╗
# # ║                       SSO LOGIN                                          ║
# # ╚══════════════════════════════════════════════════════════════════════════╝

# async def service_sso_login(
#     db: AsyncSession,
#     *,
#     provider:       str,
#     provider_token: str,
#     terms_accepted: bool,
#     ip_address:     str | None,
# ) -> dict:
#     provider = provider.lower()

#     if provider == "google":
#         user_info = await _verify_google_token(provider_token)
#     elif provider == "microsoft":
#         user_info = await _verify_microsoft_token(provider_token)
#     elif provider == "linkedin":
#         user_info = await _exchange_linkedin_code(provider_token)
#     else:
#         raise ValueError(f"Unsupported SSO provider: {provider}")

#     email      = user_info["email"].strip().lower()
#     first_name = user_info["first_name"]
#     last_name  = user_info["last_name"]

#     user = await db_get_by_field(db, User, "email", email)

#     if not user:
#         # ── New SSO user ───────────────────────────────────────────────────
#         user = User(
#             first_name        = first_name,
#             last_name         = last_name,
#             email             = email,
#             password_hash     = None,
#             auth_provider     = provider,
#             is_active         = True,
#             is_verified       = True,
#             terms_accepted    = terms_accepted,
#             terms_accepted_at = utc_now() if terms_accepted else None,
#         )
#         user = await db_create(db, user)

#         profile = UserProfile(
#             user_id         = user.id,
#             onboarding_step = 1,
#             full_legal_name = f"{first_name} {last_name}",
#             created_by      = user.id,
#             modified_by     = user.id,
#         )
#         await db_create(db, profile)

#         role_obj = await db.scalar(select(Role).where(Role.name == "employee"))
#         if not role_obj:
#             raise Exception("RBAC not seeded. Run seed migration first.")
#         await db_create(db, UserRole(
#             user_id     = user.id,
#             role_id     = role_obj.id,
#             assigned_by = user.id,
#             created_by  = user.id,
#             modified_by = user.id,
#         ))
#     else:
#         # ── Existing user — update provider if needed ──────────────────────
#         if user.auth_provider == "email":
#             await db_update(db, User, user.id, {"auth_provider": provider})

#     roles        = await get_user_role(db, user.id)
#     user_profile = await get_user_profile(db, user.id)

#     access_token = create_access_token(str(user.id),roles,user.email,user.first_name,user.last_name,)
#     refresh_token = create_refresh_token(str(user.id))
#     await _store_refresh_token(str(user.id), refresh_token)

#     return {
#         "access_token":    access_token,
#         "refresh_token":   refresh_token,
#         "roles":           roles,
#         "profile_picture":    user_profile.profile_picture_url if user_profile else None,
#         "theme_color":        user_profile.theme_color         if user_profile else None,  # ← add
#         "tour_employee_seen": user_profile.tour_employee_seen  if user_profile else False,
#         "tour_hr_seen":       user_profile.tour_hr_seen        if user_profile else False,
#         "tour_attorney_seen": user_profile.tour_attorney_seen  if user_profile else False,
#         "tour_admin_seen":    user_profile.tour_admin_seen     if user_profile else False,
#         "user": {
#             "first_name": user.first_name,
#             "last_name":  user.last_name,
#             "email":      user.email,
#             "phone":      user.phone,
#         },
#         "onboarding_step": 1,
#     }


# # ╔══════════════════════════════════════════════════════════════════════════╗
# # ║                       TOKEN REFRESH                                      ║
# # ╚══════════════════════════════════════════════════════════════════════════╝

# async def service_refresh_token(db: AsyncSession, *, refresh_token: str) -> dict:
#     """
#     Exchange a valid refresh token for a new access + refresh token pair.
#     Raises UnauthorizedException if invalid or revoked.
#     """
#     from app.core.security import decode_token
#     from jose import JWTError

#     try:
#         payload  = decode_token(refresh_token)
#         user_id  = payload.get("sub")
#         tok_type = payload.get("type")
#         if not user_id or tok_type != "refresh":
#             raise UnauthorizedException("Invalid refresh token")
#     except JWTError:
#         raise UnauthorizedException("Invalid or expired refresh token")

#     stored = await redis_get(f"refresh:{user_id}")
#     if stored != refresh_token:
#         raise UnauthorizedException("Refresh token has been revoked")

#     user = await db_get_by_id(db, User, uuid.UUID(user_id))
#     if not user or not user.is_active:
#         raise UnauthorizedException("User not found or inactive")

#     roles = await get_user_role(db, user.id)

#     new_access  =  create_access_token(str(user.id),roles,user.email,user.first_name,user.last_name,)
#     new_refresh = create_refresh_token(str(user.id))
#     await _store_refresh_token(str(user.id), new_refresh)

#     return {"access_token": new_access, "refresh_token": new_refresh}


# # ╔══════════════════════════════════════════════════════════════════════════╗
# # ║                       LOGOUT                                             ║
# # ╚══════════════════════════════════════════════════════════════════════════╝

# async def service_logout(user_id: uuid.UUID) -> None:
#     """Invalidate the user's refresh token in Redis."""
#     await redis_delete(f"refresh:{user_id}")


# # ╔══════════════════════════════════════════════════════════════════════════╗
# # ║                       PASSWORD RESET                                     ║
# # ╚══════════════════════════════════════════════════════════════════════════╝

# async def service_request_password_reset(
#     db: AsyncSession, *, email: str
# ) -> PasswordResetToken:
#     user = await db_get_by_field(db, User, "email", email.lower().strip())
#     if not user:
#         return None   # silent — don't reveal whether email exists

#     otp        = generate_otp(6)
#     otp_hash   = hash_otp(otp)
#     expires_at = utc_now() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

#     token = PasswordResetToken(
#         user_id         = user.id,
#         requested_email = email,
#         otp_code        = otp,
#         otp_code_hash   = otp_hash,
#         expires_at      = expires_at,
#         status          = ResetTokenStatus.PENDING.value,
#         resend_count    = 0,
#         failed_attempts = 0,
#     )
#     token = await db_create(db, token)
#     await redis_set(f"pwd_reset:{token.id}", otp, OTP_EXPIRE_SECONDS)

#     token._plain_otp = otp   # transient attr for caller to send email
#     return token


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


# async def service_complete_password_reset(
#     db: AsyncSession,
#     *,
#     reset_token_id: str,
#     new_password: str,
# ) -> User:
#     token = await db_get_by_id(db, PasswordResetToken, uuid.UUID(reset_token_id))
#     if not token or token.status != "verified":
#         raise BadRequestException("OTP not verified or request expired")

#     user = await db_get_by_id(db, User, token.user_id)
#     if not user:
#         raise NotFoundException("User not found")

#     await db_update(db, User, user.id, {"password_hash": hash_password(new_password)})
#     await db_update(db, PasswordResetToken, token.id, {
#         "status":                      "completed",
#         "password_reset_completed":    True,
#         "password_reset_completed_at": utc_now(),
#     })
#     return user


# # ╔══════════════════════════════════════════════════════════════════════════╗
# # ║                  SSO PROVIDER HELPERS                                    ║
# # ╚══════════════════════════════════════════════════════════════════════════╝

# async def _verify_google_token(access_token: str) -> dict:
#     async with httpx.AsyncClient() as client:
#         res = await client.get(
#             "https://www.googleapis.com/oauth2/v3/userinfo",
#             headers={"Authorization": f"Bearer {access_token}"},
#         )
#     if res.status_code != 200:
#         raise ValueError("Invalid Google token")
#     data = res.json()
#     return {
#         "email":       data["email"],
#         "first_name":  data.get("given_name") or (data.get("name", "").split()[0] if data.get("name") else ""),
#         "last_name":   data.get("family_name") or (" ".join(data.get("name", "").split()[1:]) if data.get("name") else ""),
#         "provider_id": data["sub"],
#     }


# async def _verify_microsoft_token(id_token_str: str) -> dict:
#     import base64, json
#     try:
#         payload_b64  = id_token_str.split(".")[1]
#         payload_b64 += "=" * (4 - len(payload_b64) % 4)
#         payload      = json.loads(base64.urlsafe_b64decode(payload_b64))
#     except Exception:
#         raise ValueError("Invalid Microsoft token")

#     email      = payload.get("email") or payload.get("preferred_username", "")
#     full_name  = payload.get("name", "")
#     name_parts = full_name.strip().split(" ", 1)
#     first_name = payload.get("given_name")  or (name_parts[0] if name_parts else "")
#     last_name  = payload.get("family_name") or (name_parts[1] if len(name_parts) > 1 else "")

#     return {
#         "email":       email.lower(),
#         "first_name":  first_name,
#         "last_name":   last_name,
#         "provider_id": payload.get("oid") or payload.get("sub", ""),
#     }


# async def _exchange_linkedin_code(code: str) -> dict:
#     import os
#     client_id     = os.environ["LINKEDIN_CLIENT_ID"]
#     client_secret = os.environ["LINKEDIN_CLIENT_SECRET"]
#     redirect_uri  = os.environ["LINKEDIN_REDIRECT_URI"]

#     async with httpx.AsyncClient() as client:
#         token_res = await client.post(
#             "https://www.linkedin.com/oauth/v2/accessToken",
#             data={
#                 "grant_type":    "authorization_code",
#                 "code":          code,
#                 "redirect_uri":  redirect_uri,
#                 "client_id":     client_id,
#                 "client_secret": client_secret,
#             },
#             headers={"Content-Type": "application/x-www-form-urlencoded"},
#         )
#         if token_res.status_code != 200:
#             raise ValueError("LinkedIn token exchange failed")

#         access_token = token_res.json()["access_token"]

#         user_res = await client.get(
#             "https://api.linkedin.com/v2/userinfo",
#             headers={"Authorization": f"Bearer {access_token}"},
#         )
#         if user_res.status_code != 200:
#             raise ValueError("LinkedIn userinfo fetch failed")
#         data = user_res.json()

#     first_name = data.get("given_name", "")
#     last_name  = data.get("family_name", "")
#     if not first_name:
#         full       = data.get("name", "")
#         parts      = full.strip().split(" ", 1)
#         first_name = parts[0] if parts else ""
#         last_name  = parts[1] if len(parts) > 1 else last_name

#     return {
#         "email":       data.get("email", "").lower(),
#         "first_name":  first_name,
#         "last_name":   last_name,
#         "provider_id": data.get("sub", ""),
#     }


"""
Authentication service functions.
PRODUCTION VERSION — per-session refresh tokens, instant revocation via token_version,
refresh-token reuse detection, security alert notifications.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from jose import JWTError
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import OTP_EXPIRE_SECONDS
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
    PasswordResetToken,
    Role,
    User,
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

    user = await db_get_by_field(db, User, "email", email.lower().strip())

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

    seen_before = (await db.execute(
        select(UserLoginHistory.id).where(
            UserLoginHistory.user_id == user.id,
            UserLoginHistory.status == "success",
            UserLoginHistory.browser == device_info["browser"],
            UserLoginHistory.os == device_info["os"],
        ).limit(1)
    )).scalar_one_or_none()

    await db_create(db, UserLoginHistory(
        user_id=user.id, status="success", auth_method="email_password",
        ip_address=ip_address, user_agent=user_agent,
        browser=device_info["browser"], os=device_info["os"], device_type=device_info["device_type"],
        city=location["city"], country=location["country"],
    ))

    if not seen_before:
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
        "profile_picture": await resolve_url(user_profile.profile_picture_url) if user_profile else None,
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
# ║                       PASSWORD CHANGE / RESET                           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

async def service_change_password(
    db: AsyncSession, *, user_id: uuid.UUID, new_password: str,
) -> None:
    """
    Authenticated 'change password' flow. Bumps token_version so all other
    sessions/devices are signed out immediately, and fires the security alert.
    """
    user = await db_get_by_id(db, User, user_id)
    if not user:
        raise NotFoundException("User not found")

    await db_update(db, User, user.id, {
        "password_hash": hash_password(new_password),
        "token_version": user.token_version + 1,
    })
    await fire_password_changed(db, user_id=user.id)


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


async def service_verify_reset_otp(
    db: AsyncSession,
    *,
    reset_token_id: str,
    otp_code: str,
) -> PasswordResetToken:
    token = await db_get_by_id(db, PasswordResetToken, uuid.UUID(reset_token_id))
    if not token or token.status not in ("pending",):
        raise BadRequestException("Invalid or expired reset request")

    cached_otp = await redis_get(f"pwd_reset:{reset_token_id}")
    if not cached_otp or cached_otp != otp_code:
        raise BadRequestException("Invalid or expired OTP code")

    token = await db_update(db, PasswordResetToken, token.id, {
        "otp_verified":    True,
        "otp_verified_at": utc_now(),
        "status":          "verified",
    })
    await redis_delete(f"pwd_reset:{reset_token_id}")
    return token


async def service_complete_password_reset(
    db: AsyncSession,
    *,
    reset_token_id: str,
    new_password: str,
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
        "status":                      "completed",
        "password_reset_completed":    True,
        "password_reset_completed_at": utc_now(),
    })

    await fire_password_changed(db, user_id=user.id)

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