# # app/services/hr/invitation_service.py
# import hashlib
# import secrets
# import string
# import uuid
# from datetime import datetime, timezone, timedelta
# from typing import Optional

# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select, func

# from app.core.email import send_email
# from app.core.security import create_access_token, create_refresh_token, new_session_id, hash_password
# from app.models.visamodels import (
#     ApplicationStatusHistory,
#     EmployerInvitation,
#     EmployerEmployee,
#     EmployerProfile,
#     UserProfile,
#     User,
#     UserEmail,
#     UserOTP,
#     Role,
#     UserRole,
#     Application,
#     VisaType,
# )

# from app.schemas.hr.invitation_schemas import (
#     InviteByEmailRequest,
#     InviteByCodeRequest,
#     AcceptInviteRequest,
#     AcceptInviteNewUserRequest,
#     RequestMergeOtpRequest,
#     AcceptInviteExistingUserRequest,
#     UpdateEmployeeRequest,
# )
# from app.services.employee.message_service import get_or_create_thread_for_participants
# from app.services.employee.services import db_create, db_get_by_id, db_update, _store_refresh_token

# OFFBOARDING_GRACE_PERIOD_DAYS = 30
# MERGE_OTP_EXPIRE_MINUTES = 10


# # =============================================================================
# # HELPERS
# # =============================================================================

# def _generate_invite_code() -> str:
#     chars = string.ascii_uppercase + string.digits
#     part1 = ''.join(secrets.choice(chars) for _ in range(4))
#     part2 = ''.join(secrets.choice(chars) for _ in range(4))
#     return f"VF-{part1}-{part2}"


# def _generate_invite_token() -> str:
#     return secrets.token_urlsafe(48)


# def _hash_passport(passport_number: str) -> str:
#     normalized = passport_number.strip().upper().replace(" ", "").replace("-", "")
#     return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# def _matches_employer_domain(email: str, employer: Optional[EmployerProfile]) -> bool:
#     """
#     True if `email`'s domain matches the employer's registered domain field.
#     Replaces the earlier "signup email exactly equals invited email" check —
#     that broke the moment someone signed up with a slightly different but
#     still-company address. Requires employer.domain to be set; if it's
#     empty (HR hasn't filled it in yet), this always returns False rather
#     than guessing.
#     """
#     if not employer or not employer.domain:
#         return False
#     domain = employer.domain.lower().strip().lstrip("@")
#     return email.lower().strip().endswith("@" + domain)


# async def _find_user_by_any_email(db: AsyncSession, email: str) -> Optional[User]:
#     """
#     Looks up a User by ANY of their verified emails — checks the
#     user_emails table (which covers both their original signup email
#     and any personal/work email they've since added and verified).
#     This is the single source of truth for "does an account already
#     exist for this email", used by both /hr/validate (account_exists)
#     and the merge-OTP flow.
#     """
#     normalized = email.lower().strip()
#     result = await db.execute(
#         select(User)
#         .join(UserEmail, UserEmail.user_id == User.id)
#         .where(UserEmail.email == normalized, UserEmail.is_verified == True)
#     )
#     return result.scalar_one_or_none()


# async def _user_verified_email_count(db: AsyncSession, user_id: uuid.UUID) -> int:
#     result = await db.execute(
#         select(func.count()).select_from(UserEmail)
#         .where(UserEmail.user_id == user_id, UserEmail.is_verified == True)
#     )
#     return result.scalar() or 0


# async def _create_verified_user_email(
#     db: AsyncSession, user_id: uuid.UUID, email: str, source: str, is_primary: bool = False,
# ) -> UserEmail:
#     row = UserEmail(
#         user_id=user_id, email=email.lower().strip(),
#         is_verified=True, is_primary=is_primary, source=source,
#     )
#     return await db_create(db, row)


# async def _send_personal_email_verification(db: AsyncSession, user_id: uuid.UUID, email: str) -> None:
#     """
#     Creates an UNVERIFIED user_emails row and emails a 6-digit code — no
#     link. Verified via the authenticated /account/verify-personal-email
#     endpoint, same as service_add_personal_email in auth_services.py, so
#     both "add a personal email from settings" and "provide one during
#     signup/merge" use one consistent verification mechanism.
#     """
#     normalized = email.lower().strip()

#     existing = await db.scalar(select(UserEmail).where(UserEmail.email == normalized))
#     if existing:
#         raise ValueError("This email is already in use by another account.")

#     code = f"{secrets.randbelow(1_000_000):06d}"
#     expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

#     row = UserEmail(
#         user_id=user_id, email=normalized, is_verified=False, is_primary=False,
#         source="personal", verify_token=code, verify_token_expires=expires_at,
#     )
#     await db_create(db, row)

#     await send_email(
#         to=normalized,
#         subject="Verify your personal email — Vyuflo",
#         body=(
#             "Add this email as a backup login for your Vyuflo account.\n\n"
#             f"Your verification code: {code}\n\n"
#             "Enter this code in Vyuflo to confirm. It expires in 15 minutes. "
#             "If you didn't request this, ignore this email."
#         ),
#     )


# async def _get_employer_profile(db: AsyncSession, hr_user_id: uuid.UUID) -> Optional[EmployerProfile]:
#     result = await db.execute(select(EmployerProfile).where(EmployerProfile.user_id == hr_user_id))
#     return result.scalars().first()


# async def get_employer_domain(db: AsyncSession, hr_user_id: uuid.UUID) -> Optional[str]:
#     """
#     Returns the HR user's own company domain (e.g. "vyusoft.com"), set
#     during employer profile setup. Powers the domain-suffix picker in the
#     invite email field — None if HR hasn't filled it in yet.
#     """
#     employer = await _get_employer_profile(db, hr_user_id)
#     return employer.domain if employer else None


# async def _resolve_invitation(
#     db: AsyncSession, invite_token: Optional[str], invite_code: Optional[str],
# ) -> Optional[EmployerInvitation]:
#     if invite_token:
#         result = await db.execute(select(EmployerInvitation).where(EmployerInvitation.invite_token == invite_token))
#         return result.scalars().first()
#     if invite_code:
#         result = await db.execute(select(EmployerInvitation).where(EmployerInvitation.invite_code == invite_code.upper().strip()))
#         return result.scalars().first()
#     return None


# def _check_invite_acceptable(invite: Optional[EmployerInvitation]) -> None:
#     """Raises ValueError with a user-facing message if this invite can't be accepted right now."""
#     if not invite:
#         raise ValueError("Invalid invite code or link.")
#     if invite.status == "revoked":
#         raise ValueError("This invitation has been revoked.")
#     if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
#         raise ValueError("This invitation has expired.")
#     if invite.max_uses and invite.used_count >= invite.max_uses:
#         raise ValueError("This invite has reached its maximum uses.")


# def _check_passport(invite: EmployerInvitation, passport_number: Optional[str]) -> None:
#     """Raises ValueError if this invite requires passport verification and it doesn't match."""
#     if not invite.invited_passport_hash:
#         return
#     if not passport_number or not passport_number.strip():
#         raise ValueError("Please enter your passport number to accept this invitation.")
#     if _hash_passport(passport_number) != invite.invited_passport_hash:
#         raise ValueError(
#             "The passport number you entered doesn't match our records. "
#             "Please check and try again, or contact your HR team."
#         )


# async def _link_employee_to_employer(
#     db: AsyncSession, invite: EmployerInvitation, employee_id: uuid.UUID,
# ) -> EmployerProfile:
#     """
#     Shared linking logic used by all three accept paths (authenticated,
#     new-user, existing-user-merge): creates the EmployerEmployee row,
#     updates UserProfile.employer_id, marks the invite accepted, auto-
#     assigns HR to existing applications, and opens the welcome message
#     thread. Returns the EmployerProfile so callers can build their
#     response message.
#     """
#     existing_link = await db.execute(
#         select(EmployerEmployee).where(
#             EmployerEmployee.employee_id == employee_id,
#             EmployerEmployee.employer_profile_id == invite.employer_profile_id,
#             EmployerEmployee.is_active == True,
#         )
#     )
#     if existing_link.scalars().first():
#         raise ValueError("You are already linked to this company.")

#     employer = await db_get_by_id(db, EmployerProfile, invite.employer_profile_id)
#     if not employer:
#         raise ValueError("Company not found.")

#     now = datetime.now(timezone.utc)

#     link = EmployerEmployee(
#         employer_id=invite.created_by, employee_id=employee_id,
#         employer_profile_id=invite.employer_profile_id, invitation_id=invite.id,
#         is_active=True, work_email=invite.invited_email, created_by=employee_id,
#     )
#     await db_create(db, link)

#     profile_result = await db.execute(select(UserProfile).where(UserProfile.user_id == employee_id))
#     profile = profile_result.scalars().first()
#     if profile:
#         await db_update(db, UserProfile, profile.id, {
#             "employer_id": invite.employer_profile_id, "invited_by": invite.created_by,
#         })

#     if invite.max_uses and invite.max_uses == 1:
#         await db_update(db, EmployerInvitation, invite.id, {
#             "status": "accepted", "accepted_by": employee_id,
#             "accepted_at": now, "used_count": invite.used_count + 1,
#         })
#     else:
#         await db_update(db, EmployerInvitation, invite.id, {
#             "used_count": invite.used_count + 1, "accepted_by": employee_id, "accepted_at": now,
#         })

#     await db.execute(
#         Application.__table__.update()
#         .where(Application.user_id == employee_id, Application.assigned_hr_id == None)
#         .values(assigned_hr_id=invite.created_by)
#     )

#     hr_user = await db_get_by_id(db, User, invite.created_by)
#     hr_name = f"{hr_user.first_name} {hr_user.last_name}".strip() if hr_user else "HR"
#     await get_or_create_thread_for_participants(
#         db=db, actor_id=invite.created_by, participant_ids=[employee_id], thread_type="direct",
#         initial_message=(
#             f"Hi! I'm {hr_name} from {employer.company_name}. "
#             "Welcome to Vyuflo — I'll be your HR contact for your immigration case. "
#             "Feel free to reach out here with any questions."
#         ),
#     )

#     return employer


# async def _issue_login_tokens(db: AsyncSession, user: User, roles: list[str]) -> tuple[str, str]:
#     """Issues a fresh access + refresh token pair, same shape as normal login/signup."""
#     session_id = new_session_id()
#     access_token = create_access_token(str(user.id), roles, user.email, user.first_name or "", user.last_name or "", user.token_version)
#     refresh_token = create_refresh_token(str(user.id), session_id)
#     await _store_refresh_token(str(user.id), session_id, refresh_token)
#     return access_token, refresh_token


# # =============================================================================
# # HR — CREATE INVITATIONS
# # =============================================================================

# async def create_email_invite(db: AsyncSession, hr_user_id: uuid.UUID, data: InviteByEmailRequest) -> EmployerInvitation:
#     employer = await _get_employer_profile(db, hr_user_id)
#     if not employer:
#         raise ValueError("Employer profile not found. Complete your company setup first.")

#     existing = await db.execute(
#         select(EmployerInvitation).where(
#             EmployerInvitation.employer_profile_id == employer.id,
#             EmployerInvitation.invited_email == data.email,
#             EmployerInvitation.status == "pending",
#         )
#     )
#     if existing.scalars().first():
#         raise ValueError(f"A pending invite already exists for {data.email}. Revoke it first.")

#     token = _generate_invite_token()
#     expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_days)

#     invite = EmployerInvitation(
#         created_by=hr_user_id, employer_profile_id=employer.id, invite_method="email",
#         invited_email=data.email.lower().strip(), invite_token=token, max_uses=1,
#         status="pending", expires_at=expires_at, personal_message=data.personal_message,
#         invited_passport_hash=_hash_passport(data.passport_number),
#     )
#     return await db_create(db, invite)


# async def create_code_invite(db: AsyncSession, hr_user_id: uuid.UUID, data: InviteByCodeRequest) -> EmployerInvitation:
#     employer = await _get_employer_profile(db, hr_user_id)
#     if not employer:
#         raise ValueError("Employer profile not found.")

#     for _ in range(5):
#         code = _generate_invite_code()
#         existing = await db.execute(select(EmployerInvitation).where(EmployerInvitation.invite_code == code))
#         if not existing.scalars().first():
#             break
#     else:
#         raise ValueError("Could not generate unique code. Try again.")

#     invite = EmployerInvitation(
#         created_by=hr_user_id, employer_profile_id=employer.id, invite_method="code",
#         invite_code=code, max_uses=data.max_uses, status="pending",
#         expires_at=None, personal_message=data.personal_message,
#     )
#     return await db_create(db, invite)


# # =============================================================================
# # HR — MANAGE INVITATIONS
# # =============================================================================

# async def get_my_invitations(db, hr_user_id, status=None, limit=50, offset=0):
#     employer = await _get_employer_profile(db, hr_user_id)
#     if not employer:
#         return [], 0
#     filters = [EmployerInvitation.employer_profile_id == employer.id]
#     if status:
#         filters.append(EmployerInvitation.status == status)
#     count_result = await db.execute(select(func.count()).select_from(EmployerInvitation).where(*filters))
#     total = count_result.scalar() or 0
#     result = await db.execute(
#         select(EmployerInvitation).where(*filters)
#         .order_by(EmployerInvitation.created_at.desc()).limit(limit).offset(offset)
#     )
#     return result.scalars().all(), total


# async def revoke_invitation(db, hr_user_id, invitation_id):
#     invite = await db_get_by_id(db, EmployerInvitation, invitation_id)
#     if not invite:
#         raise ValueError("Invitation not found.")
#     if invite.created_by != hr_user_id:
#         raise PermissionError("You can only revoke your own invitations.")
#     if invite.status != "pending":
#         raise ValueError(f"Cannot revoke a '{invite.status}' invitation.")
#     return await db_update(db, EmployerInvitation, invitation_id, {
#         "status": "revoked", "revoked_by": hr_user_id, "revoked_at": datetime.now(timezone.utc),
#     })


# async def resend_email_invite(db, hr_user_id, invitation_id):
#     invite = await db_get_by_id(db, EmployerInvitation, invitation_id)
#     if not invite:
#         raise ValueError("Invitation not found.")
#     if invite.created_by != hr_user_id:
#         raise PermissionError("You can only resend your own invitations.")
#     if invite.invite_method != "email":
#         raise ValueError("Only email invites can be resent.")
#     new_token = _generate_invite_token()
#     new_expiry = datetime.now(timezone.utc) + timedelta(days=7)
#     return await db_update(db, EmployerInvitation, invitation_id, {
#         "invite_token": new_token, "expires_at": new_expiry, "status": "pending",
#     })


# # =============================================================================
# # EMPLOYEE — VALIDATE
# # =============================================================================

# async def validate_invite(
#     db: AsyncSession,
#     invite_token: Optional[str],
#     invite_code: Optional[str],
#     additional_email: Optional[str] = None,
#     is_primary: Optional[bool] = None,
# ) -> dict:
#     """
#     Public endpoint. additional_email/is_primary are accepted for forward
#     compatibility with a future "which email is primary" classification
#     step, but aren't required for the current account_exists check — that
#     check is based purely on the invite's own invited_email.
#     """
#     invite = await _resolve_invitation(db, invite_token, invite_code)

#     if not invite:
#         return {"valid": False, "message": "Invalid invite code or link."}
#     if invite.status == "revoked":
#         return {"valid": False, "message": "This invitation has been revoked."}
#     if invite.status == "expired":
#         return {"valid": False, "message": "This invitation has expired."}
#     if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
#         await db_update(db, EmployerInvitation, invite.id, {"status": "expired"})
#         return {"valid": False, "message": "This invitation has expired."}
#     if invite.max_uses and invite.used_count >= invite.max_uses:
#         return {"valid": False, "message": "This invite has reached its maximum uses."}
#     if invite.status not in ("pending",):
#         return {"valid": False, "message": "This invitation is no longer valid."}

#     employer = await db_get_by_id(db, EmployerProfile, invite.employer_profile_id)
#     hr_user = await db_get_by_id(db, User, invite.created_by)
#     hr_name = f"{hr_user.first_name} {hr_user.last_name}".strip() if hr_user else "HR Team"

#     # Does an account already exist for the invited email? This is what
#     # decides whether the frontend shows "Log in" or "Sign up" — checking
#     # actual account existence instead of the current browser session,
#     # which could belong to a totally different logged-in person.
#     account_exists = False
#     if invite.invited_email:
#         matched_user = await _find_user_by_any_email(db, invite.invited_email)
#         account_exists = matched_user is not None

#     return {
#         "valid": True,
#         "company_name": employer.company_name if employer else "Unknown Company",
#         "hr_name": hr_name,
#         "invite_method": invite.invite_method,
#         "invited_email": invite.invited_email,
#         "message": f"Valid invite from {employer.company_name if employer else 'a company'}",
#         "requires_passport_verification": bool(invite.invited_passport_hash),
#         "account_exists": account_exists,
#     }


# # =============================================================================
# # EMPLOYEE — ACCEPT (authenticated — person already has a session)
# # =============================================================================

# async def accept_invite(db: AsyncSession, employee_id: uuid.UUID, data: AcceptInviteRequest) -> dict:
#     invite = await _resolve_invitation(db, data.invite_token, data.invite_code)
#     _check_invite_acceptable(invite)
#     _check_passport(invite, data.passport_number)

#     employer = await _link_employee_to_employer(db, invite, employee_id)

#     employee_user = await db_get_by_id(db, User, employee_id)

#     # Domain-based check, replacing the old exact-email-match heuristic.
#     # True only if their current email matches the employer's registered
#     # domain AND they don't already have a second verified email on file
#     # (i.e. they haven't already added a personal backup before).
#     needs_personal_email = (
#         _matches_employer_domain(employee_user.email, employer)
#         and (await _user_verified_email_count(db, employee_id)) <= 1
#     )

#     return {
#         "message": f"Successfully linked to {employer.company_name}",
#         "company_name": employer.company_name,
#         "employer_id": invite.employer_profile_id,
#         "needs_personal_email": needs_personal_email,
#     }


# # =============================================================================
# # EMPLOYEE — ACCEPT (public — no existing account)
# # =============================================================================

# async def accept_invite_new_user(db: AsyncSession, data: AcceptInviteNewUserRequest) -> dict:
#     """
#     Used when GET /hr/validate returned account_exists: false. Creates a
#     brand-new account, links it to the employer, and logs the person in —
#     all in one call, since the passport check already confirmed identity.
#     This replaces the earlier multi-step "sign up → verify email → set up
#     profile → come back to accept" journey with a single form.
#     """
#     invite = await _resolve_invitation(db, data.invite_token, data.invite_code)
#     _check_invite_acceptable(invite)
#     _check_passport(invite, data.passport_number)

#     normalized_email = data.email.lower().strip()
#     existing = await db.scalar(select(User).where(User.email == normalized_email))
#     if existing:
#         raise ValueError("An account with this email already exists. Try logging in instead.")

#     employer_profile_for_check = await db_get_by_id(db, EmployerProfile, invite.employer_profile_id)
#     is_domain_email = _matches_employer_domain(normalized_email, employer_profile_for_check)

#     user = User(
#         first_name=data.first_name, last_name=data.last_name, email=normalized_email,
#         password_hash=hash_password(data.password), auth_provider="email",
#         is_active=True, is_verified=True,  # passport check already confirmed identity
#         terms_accepted=data.terms_accepted,
#         terms_accepted_at=datetime.now(timezone.utc) if data.terms_accepted else None,
#     )
#     user = await db_create(db, user)

#     profile = UserProfile(
#         user_id=user.id, onboarding_step=1, onboarding_completed=True,
#         full_legal_name=f"{data.first_name} {data.last_name}",
#         created_by=user.id, modified_by=user.id,
#     )
#     await db_create(db, profile)

#     role_obj = await db.scalar(select(Role).where(Role.name == "employee"))
#     if not role_obj:
#         raise Exception("RBAC not seeded. Run seed migration first.")
#     await db_create(db, UserRole(user_id=user.id, role_id=role_obj.id, assigned_by=user.id, created_by=user.id, modified_by=user.id))

#     await _create_verified_user_email(db, user.id, normalized_email, source="work" if is_domain_email else "signup", is_primary=True)

#     other_email_added = False
#     if data.other_email and data.other_email.lower().strip() != normalized_email:
#         await _send_personal_email_verification(db, user.id, data.other_email)
#         other_email_added = True

#     employer = await _link_employee_to_employer(db, invite, user.id)
#     access_token, refresh_token = await _issue_login_tokens(db, user, ["employee"])

#     # Domain-matched AND they didn't already add a personal email in this
#     # same form — ask once more, right after joining, instead of letting
#     # the optional field's being skipped mean they never get asked at all.
#     needs_personal_email = is_domain_email and not other_email_added

#     return {
#         "access_token": access_token, "refresh_token": refresh_token, "roles": ["employee"],
#         "company_name": employer.company_name, "employer_id": invite.employer_profile_id,
#         "linked_email": data.other_email,
#         "needs_personal_email": needs_personal_email,
#         "message": f"Welcome to {employer.company_name}! Your account has been created.",
#     }


# # =============================================================================
# # EMPLOYEE — ACCEPT (public — existing account, merge via OTP)
# # =============================================================================

# async def request_merge_otp(db: AsyncSession, data: RequestMergeOtpRequest) -> dict:
#     """
#     Step 1 of the merge flow. Used when GET /hr/validate returned
#     account_exists: true, but the person opening the invite link isn't
#     currently logged in (so we can't just use their session). Sends a
#     one-time code to the matched account's email to confirm it's really
#     them before merging the new employer link into that account.
#     """
#     invite = await _resolve_invitation(db, data.invite_token, data.invite_code)
#     _check_invite_acceptable(invite)

#     user = await _find_user_by_any_email(db, data.login_email)
#     if not user:
#         raise ValueError("No account found with that email.")

#     otp_code = f"{secrets.randbelow(1_000_000):06d}"
#     expires_at = datetime.now(timezone.utc) + timedelta(minutes=MERGE_OTP_EXPIRE_MINUTES)

#     await db_create(db, UserOTP(
#         user_id=user.id, otp_code=otp_code, otp_type="merge_invite",
#         is_used=False, expires_at=expires_at, created_by=user.id,
#     ))

#     await send_email(
#         to=data.login_email,
#         subject="Your Vyuflo verification code",
#         body=(
#             f"Your verification code is: {otp_code}\n\n"
#             f"It expires in {MERGE_OTP_EXPIRE_MINUTES} minutes. "
#             "Enter this code to confirm it's you and link this invitation to your account."
#         ),
#     )
#     return {"message": "Verification code sent to your email."}


# async def accept_invite_existing_user(db: AsyncSession, data: AcceptInviteExistingUserRequest) -> dict:
#     """
#     Step 2 of the merge flow. Confirms the OTP from request_merge_otp,
#     then links the invite to the matched account exactly like the
#     authenticated accept path, and logs the person in.
#     """
#     invite = await _resolve_invitation(db, data.invite_token, data.invite_code)
#     _check_invite_acceptable(invite)

#     user = await _find_user_by_any_email(db, data.login_email)
#     if not user:
#         raise ValueError("No account found with that email.")

#     otp_result = await db.execute(
#         select(UserOTP).where(
#             UserOTP.user_id == user.id, UserOTP.otp_code == data.otp_code,
#             UserOTP.otp_type == "merge_invite", UserOTP.is_used == False,
#         ).order_by(UserOTP.created_at.desc()).limit(1)
#     )
#     otp = otp_result.scalars().first()
#     if not otp or otp.expires_at < datetime.now(timezone.utc):
#         raise ValueError("Invalid or expired verification code. Please request a new one.")

#     await db_update(db, UserOTP, otp.id, {"is_used": True})

#     _check_passport(invite, data.passport_number)

#     employer = await _link_employee_to_employer(db, invite, user.id)

#     other_email_added = False
#     if data.other_email and data.other_email.lower().strip() != user.email.lower().strip():
#         try:
#             await _send_personal_email_verification(db, user.id, data.other_email)
#             other_email_added = True
#         except ValueError:
#             pass  # already in use elsewhere — don't block acceptance over this

#     roles_result = await db.execute(
#         select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user.id)
#     )
#     roles = [r for r, in roles_result.all()] or ["employee"]

#     access_token, refresh_token = await _issue_login_tokens(db, user, roles)

#     # Same domain-match check as the new-user path — an EXISTING account
#     # can still be domain-email-only if they'd never added a backup before.
#     is_domain_email = _matches_employer_domain(user.email, employer)
#     needs_personal_email = (
#         is_domain_email and not other_email_added
#         and (await _user_verified_email_count(db, user.id)) <= 1
#     )

#     return {
#         "access_token": access_token, "refresh_token": refresh_token, "roles": roles,
#         "company_name": employer.company_name, "employer_id": invite.employer_profile_id,
#         "linked_email": data.other_email,
#         "needs_personal_email": needs_personal_email,
#         "message": f"Successfully linked to {employer.company_name}.",
#     }


# # =============================================================================
# # HR — MANAGE EMPLOYEES
# # =============================================================================

# async def get_my_employees(db, hr_user_id, is_active=True, limit=50, offset=0):
#     employer = await _get_employer_profile(db, hr_user_id)
#     if not employer:
#         return [], 0
#     filters = [EmployerEmployee.employer_id == hr_user_id]
#     if is_active is not None:
#         filters.append(EmployerEmployee.is_active == is_active)
#     count_result = await db.execute(select(func.count()).select_from(EmployerEmployee).where(*filters))
#     total = count_result.scalar() or 0
#     result = await db.execute(
#         select(EmployerEmployee).where(*filters).order_by(EmployerEmployee.created_at.desc()).limit(limit).offset(offset)
#     )
#     employee_links = result.scalars().all()

#     employees = []
#     for link in employee_links:
#         emp_user = await db_get_by_id(db, User, link.employee_id)
#         emp_profile_result = await db.execute(select(UserProfile).where(UserProfile.user_id == link.employee_id))
#         emp_profile = emp_profile_result.scalars().first()

#         app_count_result = await db.execute(
#             select(func.count()).select_from(Application).where(
#                 Application.user_id == link.employee_id, Application.assigned_hr_id == hr_user_id,
#                 Application.status.in_(["draft", "in_progress", "action_needed", "submitted", "rfe_response"]),
#             )
#         )
#         active_apps = app_count_result.scalar() or 0

#         if emp_user:
#             full_name = emp_profile.full_legal_name if emp_profile and emp_profile.full_legal_name \
#                 else f"{emp_user.first_name} {emp_user.last_name}".strip()
#             employees.append({
#                 "id": link.id, "employee_id": link.employee_id, "full_name": full_name,
#                 "email": emp_user.email, "profile_picture_url": emp_profile.profile_picture_url if emp_profile else None,
#                 "job_title": link.job_title, "department": link.department, "work_email": link.work_email,
#                 "start_date": str(link.start_date) if link.start_date else None, "is_active": link.is_active,
#                 "access_revoked_at": link.access_revoked_at.isoformat() if link.access_revoked_at else None,
#                 "active_applications": active_apps, "pending_documents": 0, "linked_at": link.created_at,
#             })
#     return employees, total


# async def update_employee_info(db, hr_user_id, employee_link_id, data: UpdateEmployeeRequest):
#     link = await db_get_by_id(db, EmployerEmployee, employee_link_id)
#     if not link:
#         raise ValueError("Employee link not found.")
#     if link.employer_id != hr_user_id:
#         raise PermissionError("You can only update your own employees.")
#     update_data = {k: v for k, v in data.model_dump(exclude_none=True).items()}
#     if not update_data:
#         return link
#     return await db_update(db, EmployerEmployee, employee_link_id, update_data)


# async def deactivate_employee(db, hr_user_id, employee_link_id):
#     link = await db_get_by_id(db, EmployerEmployee, employee_link_id)
#     if not link:
#         raise ValueError("Employee link not found.")
#     if link.employer_id != hr_user_id:
#         raise PermissionError("You can only remove your own employees.")
#     now = datetime.now(timezone.utc)
#     grace_end = now + timedelta(days=OFFBOARDING_GRACE_PERIOD_DAYS)
#     return await db_update(db, EmployerEmployee, employee_link_id, {
#         "end_date": now.date(), "access_revoked_at": grace_end,
#     })


# async def get_employee_detail(db, hr_user_id, employee_link_id):
#     link = await db_get_by_id(db, EmployerEmployee, employee_link_id)
#     if not link:
#         raise ValueError("Employee link not found.")
#     if link.employer_id != hr_user_id:
#         raise PermissionError("You can only view your own employees.")

#     emp_user = await db_get_by_id(db, User, link.employee_id)
#     emp_profile_result = await db.execute(select(UserProfile).where(UserProfile.user_id == link.employee_id))
#     emp_profile = emp_profile_result.scalars().first()
#     employer = await _get_employer_profile(db, hr_user_id)

#     full_name = (emp_profile.full_legal_name if emp_profile and emp_profile.full_legal_name
#                  else f"{emp_user.first_name} {emp_user.last_name}".strip() if emp_user else "Unknown")

#     apps_result = await db.execute(select(Application).where(Application.user_id == link.employee_id).order_by(Application.created_at.desc()))
#     all_apps = apps_result.scalars().all()
#     active_statuses = {"in_progress", "action_needed", "rfe_response", "submitted"}
#     active_apps = [a for a in all_apps if a.status in active_statuses]
#     primary_case = active_apps[0] if active_apps else None

#     async def _build_app_summary(app):
#         vt_result = await db.execute(select(VisaType).where(VisaType.id == app.visa_type_id))
#         vt = vt_result.scalars().first()
#         attorney = await db_get_by_id(db, User, app.assigned_attorney_id) if app.assigned_attorney_id else None
#         history_result = await db.execute(
#             select(ApplicationStatusHistory).where(ApplicationStatusHistory.application_id == app.id)
#             .order_by(ApplicationStatusHistory.created_at.desc()).limit(1)
#         )
#         latest_history = history_result.scalars().first()
#         return {
#             "id": str(app.id), "application_number": app.application_number,
#             "visa_type_code": vt.code if vt else "—", "visa_type_name": f"{vt.code} Extension" if vt else "Unknown",
#             "status": app.status, "current_stage": app.current_stage, "progress_percent": app.progress_percent,
#             "start_date": str(app.start_date) if app.start_date else None, "due_date": str(app.due_date) if app.due_date else None,
#             "next_milestone": latest_history.stage.replace("_", " ").title() if latest_history else None,
#             "assigned_attorney_name": f"{attorney.first_name} {attorney.last_name}".strip() if attorney else None,
#             "assigned_attorney_avatar": None,
#         }

#     all_cases_summary = [await _build_app_summary(a) for a in all_apps]
#     active_case_summary = await _build_app_summary(primary_case) if primary_case else None

#     from app.models.visamodels import Document
#     from sqlalchemy.orm import joinedload
#     docs_result = await db.execute(
#         select(Document).options(joinedload(Document.document_type))
#         .where(Document.user_id == link.employee_id).order_by(Document.updated_at.desc()).limit(12)
#     )
#     docs = docs_result.unique().scalars().all()
#     documents_summary = [{
#         "id": str(doc.id), "name": doc.document_type.name if doc.document_type else doc.file_name,
#         "status": doc.status, "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
#         "file_format": doc.file_format,
#     } for doc in docs]

#     from app.models.visamodels import Deadline
#     verified_docs = sum(1 for d in docs if d.status == "verified")
#     deadline_result = await db.execute(
#         select(Deadline).where(
#             Deadline.user_id == link.employee_id, Deadline.is_completed == False,
#             Deadline.is_dismissed == False, Deadline.due_date >= datetime.now(timezone.utc),
#         ).order_by(Deadline.due_date.asc()).limit(1)
#     )
#     next_deadline = deadline_result.scalars().first()
#     next_deadline_days = max(0, (next_deadline.due_date - datetime.now(timezone.utc)).days) if next_deadline else None

#     stats = {
#         "active_cases": len(active_apps), "total_cases": len(all_apps),
#         "documents_total": len(docs), "documents_verified": verified_docs,
#         "next_deadline_days": next_deadline_days,
#     }

#     history_result = await db.execute(
#         select(ApplicationStatusHistory).where(ApplicationStatusHistory.application_id.in_([a.id for a in all_apps]))
#         .order_by(ApplicationStatusHistory.created_at.desc()).limit(10)
#     )
#     history_items = history_result.scalars().all()
#     dot_map = {"approved": "green", "submitted": "blue", "action_needed": "orange", "rfe_response": "orange",
#                "in_progress": "blue", "draft": "gray", "rejected": "gray", "withdrawn": "gray"}
#     activity = []
#     for h in history_items:
#         actor_user = await db_get_by_id(db, User, h.changed_by) if h.changed_by else None
#         actor_label = f"{actor_user.first_name} {actor_user.last_name}".strip() if actor_user else "System"
#         activity.append({
#             "id": str(h.id), "title": f"{h.status.replace('_', ' ').title()} — {h.stage.replace('_', ' ').title()}",
#             "actor": f"By {actor_label}", "occurred_at": h.created_at.isoformat(), "dot_color": dot_map.get(h.status, "gray"),
#         })

#     visa_code = None
#     if all_apps:
#         latest_vt_result = await db.execute(select(VisaType).where(VisaType.id == all_apps[0].visa_type_id))
#         latest_vt = latest_vt_result.scalars().first()
#         if latest_vt:
#             visa_code = latest_vt.code

#     return {
#         "profile": {
#             "employee_link_id": str(link.id), "user_id": str(link.employee_id), "full_name": full_name,
#             "email": emp_user.email if emp_user else "", "profile_picture_url": emp_profile.profile_picture_url if emp_profile else None,
#             "job_title": link.job_title, "department": link.department, "work_email": link.work_email,
#             "start_date": str(link.start_date) if link.start_date else None,
#             "company_name": employer.company_name if employer else None,
#             "company_location": f"{employer.city}, {employer.state}".strip(", ") if employer and employer.city else None,
#             "visa_code": visa_code, "visa_status_label": "Active" if active_apps else "No Active Visa",
#             "linked_at": link.created_at.isoformat(), "is_active": link.is_active,
#         },
#         "stats": stats, "active_case": active_case_summary, "all_cases": all_cases_summary,
#         "documents": documents_summary, "activity": activity,
#     }


# app/services/hr/invitation_service.py
import hashlib
import secrets
import string
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.email import send_email
from app.core.security import create_access_token, create_refresh_token, new_session_id, hash_password
from app.models.visamodels import (
    ApplicationStatusHistory,
    EmployerInvitation,
    EmployerEmployee,
    EmployerProfile,
    UserProfile,
    User,
    UserEmail,
    UserOTP,
    Role,
    UserRole,
    Application,
    VisaType,
)

from app.schemas.hr.invitation_schemas import (
    InviteByEmailRequest,
    InviteByCodeRequest,
    AcceptInviteRequest,
    AcceptInviteNewUserRequest,
    RequestMergeOtpRequest,
    AcceptInviteExistingUserRequest,
    UpdateEmployeeRequest,
)
from app.services.employee.message_service import get_or_create_thread_for_participants
from app.services.employee.services import db_create, db_get_by_id, db_update, _store_refresh_token
from app.services.admin.system_settings import get_setting_value

OFFBOARDING_GRACE_PERIOD_DAYS = 30
MERGE_OTP_EXPIRE_MINUTES = 10

# Fallback used only if the "invitations.default_expiry_days" setting is
# somehow missing from the DB entirely (e.g. seed hasn't run yet). Once
# seeded, the actual admin-configured value always wins over this.
FALLBACK_INVITE_EXPIRY_DAYS = 7


# =============================================================================
# HELPERS
# =============================================================================

def _generate_invite_code() -> str:
    chars = string.ascii_uppercase + string.digits
    part1 = ''.join(secrets.choice(chars) for _ in range(4))
    part2 = ''.join(secrets.choice(chars) for _ in range(4))
    return f"VF-{part1}-{part2}"


def _generate_invite_token() -> str:
    return secrets.token_urlsafe(48)


def _hash_passport(passport_number: str) -> str:
    normalized = passport_number.strip().upper().replace(" ", "").replace("-", "")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _matches_employer_domain(email: str, employer: Optional[EmployerProfile]) -> bool:
    """
    True if `email`'s domain matches the employer's registered domain field.
    Replaces the earlier "signup email exactly equals invited email" check —
    that broke the moment someone signed up with a slightly different but
    still-company address. Requires employer.domain to be set; if it's
    empty (HR hasn't filled it in yet), this always returns False rather
    than guessing.
    """
    if not employer or not employer.domain:
        return False
    domain = employer.domain.lower().strip().lstrip("@")
    return email.lower().strip().endswith("@" + domain)


async def _find_user_by_any_email(db: AsyncSession, email: str) -> Optional[User]:
    """
    Looks up a User by ANY of their verified emails — checks the
    user_emails table (which covers both their original signup email
    and any personal/work email they've since added and verified).
    This is the single source of truth for "does an account already
    exist for this email", used by both /hr/validate (account_exists)
    and the merge-OTP flow.
    """
    normalized = email.lower().strip()
    result = await db.execute(
        select(User)
        .join(UserEmail, UserEmail.user_id == User.id)
        .where(UserEmail.email == normalized, UserEmail.is_verified == True)
    )
    return result.scalar_one_or_none()


async def _user_verified_email_count(db: AsyncSession, user_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count()).select_from(UserEmail)
        .where(UserEmail.user_id == user_id, UserEmail.is_verified == True)
    )
    return result.scalar() or 0


async def _create_verified_user_email(
    db: AsyncSession, user_id: uuid.UUID, email: str, source: str, is_primary: bool = False,
) -> UserEmail:
    row = UserEmail(
        user_id=user_id, email=email.lower().strip(),
        is_verified=True, is_primary=is_primary, source=source,
    )
    return await db_create(db, row)


async def _send_personal_email_verification(db: AsyncSession, user_id: uuid.UUID, email: str) -> None:
    """
    Creates an UNVERIFIED user_emails row and emails a 6-digit code — no
    link. Verified via the authenticated /account/verify-personal-email
    endpoint, same as service_add_personal_email in auth_services.py, so
    both "add a personal email from settings" and "provide one during
    signup/merge" use one consistent verification mechanism.
    """
    normalized = email.lower().strip()

    existing = await db.scalar(select(UserEmail).where(UserEmail.email == normalized))
    if existing:
        raise ValueError("This email is already in use by another account.")

    code = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    row = UserEmail(
        user_id=user_id, email=normalized, is_verified=False, is_primary=False,
        source="personal", verify_token=code, verify_token_expires=expires_at,
    )
    await db_create(db, row)

    await send_email(
        to=normalized,
        subject="Verify your personal email — Vyuflo",
        body=(
            "Add this email as a backup login for your Vyuflo account.\n\n"
            f"Your verification code: {code}\n\n"
            "Enter this code in Vyuflo to confirm. It expires in 15 minutes. "
            "If you didn't request this, ignore this email."
        ),
    )


async def _get_employer_profile(db: AsyncSession, hr_user_id: uuid.UUID) -> Optional[EmployerProfile]:
    result = await db.execute(select(EmployerProfile).where(EmployerProfile.user_id == hr_user_id))
    return result.scalars().first()


async def get_employer_domain(db: AsyncSession, hr_user_id: uuid.UUID) -> Optional[str]:
    """
    Returns the HR user's own company domain (e.g. "vyusoft.com"), set
    during employer profile setup. Powers the domain-suffix picker in the
    invite email field — None if HR hasn't filled it in yet.
    """
    employer = await _get_employer_profile(db, hr_user_id)
    return employer.domain if employer else None


async def _resolve_invite_expiry_days(db: AsyncSession, requested_days: Optional[int]) -> int:
    """
    HR can still override the expiry per-invite by explicitly passing
    expires_days on the request (validated 1-30 by the schema). If they
    don't, this falls back to the org-wide default set by an app_admin in
    Admin > System Settings > Invitations ("invitations.default_expiry_days").
    If that setting is somehow missing (e.g. seed hasn't run), falls back
    to a hardcoded 7 days rather than raising.
    """
    if requested_days is not None:
        return requested_days
    raw = await get_setting_value(db, "invitations.default_expiry_days")
    if raw is None:
        return FALLBACK_INVITE_EXPIRY_DAYS
    try:
        return int(raw)
    except (TypeError, ValueError):
        return FALLBACK_INVITE_EXPIRY_DAYS


async def _resolve_invitation(
    db: AsyncSession, invite_token: Optional[str], invite_code: Optional[str],
) -> Optional[EmployerInvitation]:
    if invite_token:
        result = await db.execute(select(EmployerInvitation).where(EmployerInvitation.invite_token == invite_token))
        return result.scalars().first()
    if invite_code:
        result = await db.execute(select(EmployerInvitation).where(EmployerInvitation.invite_code == invite_code.upper().strip()))
        return result.scalars().first()
    return None


def _check_invite_acceptable(invite: Optional[EmployerInvitation]) -> None:
    """Raises ValueError with a user-facing message if this invite can't be accepted right now."""
    if not invite:
        raise ValueError("Invalid invite code or link.")
    if invite.status == "revoked":
        raise ValueError("This invitation has been revoked.")
    if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
        raise ValueError("This invitation has expired.")
    if invite.max_uses and invite.used_count >= invite.max_uses:
        raise ValueError("This invite has reached its maximum uses.")


def _check_passport(invite: EmployerInvitation, passport_number: Optional[str]) -> None:
    """Raises ValueError if this invite requires passport verification and it doesn't match."""
    if not invite.invited_passport_hash:
        return
    if not passport_number or not passport_number.strip():
        raise ValueError("Please enter your passport number to accept this invitation.")
    if _hash_passport(passport_number) != invite.invited_passport_hash:
        raise ValueError(
            "The passport number you entered doesn't match our records. "
            "Please check and try again, or contact your HR team."
        )


async def _link_employee_to_employer(
    db: AsyncSession, invite: EmployerInvitation, employee_id: uuid.UUID,
) -> EmployerProfile:
    """
    Shared linking logic used by all three accept paths (authenticated,
    new-user, existing-user-merge): creates the EmployerEmployee row,
    updates UserProfile.employer_id, marks the invite accepted, auto-
    assigns HR to existing applications, and opens the welcome message
    thread. Returns the EmployerProfile so callers can build their
    response message.
    """
    existing_link = await db.execute(
        select(EmployerEmployee).where(
            EmployerEmployee.employee_id == employee_id,
            EmployerEmployee.employer_profile_id == invite.employer_profile_id,
            EmployerEmployee.is_active == True,
        )
    )
    if existing_link.scalars().first():
        raise ValueError("You are already linked to this company.")

    employer = await db_get_by_id(db, EmployerProfile, invite.employer_profile_id)
    if not employer:
        raise ValueError("Company not found.")

    now = datetime.now(timezone.utc)

    link = EmployerEmployee(
        employer_id=invite.created_by, employee_id=employee_id,
        employer_profile_id=invite.employer_profile_id, invitation_id=invite.id,
        is_active=True, work_email=invite.invited_email, created_by=employee_id,
    )
    await db_create(db, link)

    profile_result = await db.execute(select(UserProfile).where(UserProfile.user_id == employee_id))
    profile = profile_result.scalars().first()
    if profile:
        await db_update(db, UserProfile, profile.id, {
            "employer_id": invite.employer_profile_id, "invited_by": invite.created_by,
        })

    if invite.max_uses and invite.max_uses == 1:
        await db_update(db, EmployerInvitation, invite.id, {
            "status": "accepted", "accepted_by": employee_id,
            "accepted_at": now, "used_count": invite.used_count + 1,
        })
    else:
        await db_update(db, EmployerInvitation, invite.id, {
            "used_count": invite.used_count + 1, "accepted_by": employee_id, "accepted_at": now,
        })

    await db.execute(
        Application.__table__.update()
        .where(Application.user_id == employee_id, Application.assigned_hr_id == None)
        .values(assigned_hr_id=invite.created_by)
    )

    hr_user = await db_get_by_id(db, User, invite.created_by)
    hr_name = f"{hr_user.first_name} {hr_user.last_name}".strip() if hr_user else "HR"
    await get_or_create_thread_for_participants(
        db=db, actor_id=invite.created_by, participant_ids=[employee_id], thread_type="direct",
        initial_message=(
            f"Hi! I'm {hr_name} from {employer.company_name}. "
            "Welcome to Vyuflo — I'll be your HR contact for your immigration case. "
            "Feel free to reach out here with any questions."
        ),
    )

    return employer


async def _issue_login_tokens(db: AsyncSession, user: User, roles: list[str]) -> tuple[str, str]:
    """Issues a fresh access + refresh token pair, same shape as normal login/signup."""
    session_id = new_session_id()
    access_token = create_access_token(str(user.id), roles, user.email, user.first_name or "", user.last_name or "", user.token_version)
    refresh_token = create_refresh_token(str(user.id), session_id)
    await _store_refresh_token(str(user.id), session_id, refresh_token)
    return access_token, refresh_token


# =============================================================================
# HR — CREATE INVITATIONS
# =============================================================================

async def create_email_invite(db: AsyncSession, hr_user_id: uuid.UUID, data: InviteByEmailRequest) -> EmployerInvitation:
    employer = await _get_employer_profile(db, hr_user_id)
    if not employer:
        raise ValueError("Employer profile not found. Complete your company setup first.")

    existing = await db.execute(
        select(EmployerInvitation).where(
            EmployerInvitation.employer_profile_id == employer.id,
            EmployerInvitation.invited_email == data.email,
            EmployerInvitation.status == "pending",
        )
    )
    if existing.scalars().first():
        raise ValueError(f"A pending invite already exists for {data.email}. Revoke it first.")

    token = _generate_invite_token()
    # CHANGED — data.expires_days is now Optional on the schema. When HR
    # doesn't explicitly set it, this reads the org-wide default from
    # Admin > System Settings > Invitations instead of a hardcoded number.
    expiry_days = await _resolve_invite_expiry_days(db, data.expires_days)
    expires_at = datetime.now(timezone.utc) + timedelta(days=expiry_days)

    invite = EmployerInvitation(
        created_by=hr_user_id, employer_profile_id=employer.id, invite_method="email",
        invited_email=data.email.lower().strip(), invite_token=token, max_uses=1,
        status="pending", expires_at=expires_at, personal_message=data.personal_message,
        invited_passport_hash=_hash_passport(data.passport_number),
    )
    return await db_create(db, invite)


async def create_code_invite(db: AsyncSession, hr_user_id: uuid.UUID, data: InviteByCodeRequest) -> EmployerInvitation:
    employer = await _get_employer_profile(db, hr_user_id)
    if not employer:
        raise ValueError("Employer profile not found.")

    for _ in range(5):
        code = _generate_invite_code()
        existing = await db.execute(select(EmployerInvitation).where(EmployerInvitation.invite_code == code))
        if not existing.scalars().first():
            break
    else:
        raise ValueError("Could not generate unique code. Try again.")

    invite = EmployerInvitation(
        created_by=hr_user_id, employer_profile_id=employer.id, invite_method="code",
        invite_code=code, max_uses=data.max_uses, status="pending",
        expires_at=None, personal_message=data.personal_message,
    )
    return await db_create(db, invite)


# =============================================================================
# HR — MANAGE INVITATIONS
# =============================================================================

async def get_my_invitations(db, hr_user_id, status=None, limit=50, offset=0):
    employer = await _get_employer_profile(db, hr_user_id)
    if not employer:
        return [], 0
    filters = [EmployerInvitation.employer_profile_id == employer.id]
    if status:
        filters.append(EmployerInvitation.status == status)
    count_result = await db.execute(select(func.count()).select_from(EmployerInvitation).where(*filters))
    total = count_result.scalar() or 0
    result = await db.execute(
        select(EmployerInvitation).where(*filters)
        .order_by(EmployerInvitation.created_at.desc()).limit(limit).offset(offset)
    )
    return result.scalars().all(), total


async def revoke_invitation(db, hr_user_id, invitation_id):
    invite = await db_get_by_id(db, EmployerInvitation, invitation_id)
    if not invite:
        raise ValueError("Invitation not found.")
    if invite.created_by != hr_user_id:
        raise PermissionError("You can only revoke your own invitations.")
    if invite.status != "pending":
        raise ValueError(f"Cannot revoke a '{invite.status}' invitation.")
    return await db_update(db, EmployerInvitation, invitation_id, {
        "status": "revoked", "revoked_by": hr_user_id, "revoked_at": datetime.now(timezone.utc),
    })


async def resend_email_invite(db, hr_user_id, invitation_id):
    invite = await db_get_by_id(db, EmployerInvitation, invitation_id)
    if not invite:
        raise ValueError("Invitation not found.")
    if invite.created_by != hr_user_id:
        raise PermissionError("You can only resend your own invitations.")
    if invite.invite_method != "email":
        raise ValueError("Only email invites can be resent.")
    new_token = _generate_invite_token()
    # CHANGED — was hardcoded to 7 days; now uses the same org-wide default
    # as a fresh invite, so resend behaves consistently with new sends.
    expiry_days = await _resolve_invite_expiry_days(db, None)
    new_expiry = datetime.now(timezone.utc) + timedelta(days=expiry_days)
    return await db_update(db, EmployerInvitation, invitation_id, {
        "invite_token": new_token, "expires_at": new_expiry, "status": "pending",
    })


# =============================================================================
# EMPLOYEE — VALIDATE
# =============================================================================

async def validate_invite(
    db: AsyncSession,
    invite_token: Optional[str],
    invite_code: Optional[str],
    additional_email: Optional[str] = None,
    is_primary: Optional[bool] = None,
) -> dict:
    """
    Public endpoint. additional_email/is_primary are accepted for forward
    compatibility with a future "which email is primary" classification
    step, but aren't required for the current account_exists check — that
    check is based purely on the invite's own invited_email.
    """
    invite = await _resolve_invitation(db, invite_token, invite_code)

    if not invite:
        return {"valid": False, "message": "Invalid invite code or link."}
    if invite.status == "revoked":
        return {"valid": False, "message": "This invitation has been revoked."}
    if invite.status == "expired":
        return {"valid": False, "message": "This invitation has expired."}
    if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
        await db_update(db, EmployerInvitation, invite.id, {"status": "expired"})
        return {"valid": False, "message": "This invitation has expired."}
    if invite.max_uses and invite.used_count >= invite.max_uses:
        return {"valid": False, "message": "This invite has reached its maximum uses."}
    if invite.status not in ("pending",):
        return {"valid": False, "message": "This invitation is no longer valid."}

    employer = await db_get_by_id(db, EmployerProfile, invite.employer_profile_id)
    hr_user = await db_get_by_id(db, User, invite.created_by)
    hr_name = f"{hr_user.first_name} {hr_user.last_name}".strip() if hr_user else "HR Team"

    # Does an account already exist for the invited email? This is what
    # decides whether the frontend shows "Log in" or "Sign up" — checking
    # actual account existence instead of the current browser session,
    # which could belong to a totally different logged-in person.
    account_exists = False
    if invite.invited_email:
        matched_user = await _find_user_by_any_email(db, invite.invited_email)
        account_exists = matched_user is not None

    return {
        "valid": True,
        "company_name": employer.company_name if employer else "Unknown Company",
        "hr_name": hr_name,
        "invite_method": invite.invite_method,
        "invited_email": invite.invited_email,
        "message": f"Valid invite from {employer.company_name if employer else 'a company'}",
        "requires_passport_verification": bool(invite.invited_passport_hash),
        "account_exists": account_exists,
    }


# =============================================================================
# EMPLOYEE — ACCEPT (authenticated — person already has a session)
# =============================================================================

async def accept_invite(db: AsyncSession, employee_id: uuid.UUID, data: AcceptInviteRequest) -> dict:
    invite = await _resolve_invitation(db, data.invite_token, data.invite_code)
    _check_invite_acceptable(invite)
    _check_passport(invite, data.passport_number)

    employer = await _link_employee_to_employer(db, invite, employee_id)

    employee_user = await db_get_by_id(db, User, employee_id)

    # Domain-based check, replacing the old exact-email-match heuristic.
    # True only if their current email matches the employer's registered
    # domain AND they don't already have a second verified email on file
    # (i.e. they haven't already added a personal backup before).
    needs_personal_email = (
        _matches_employer_domain(employee_user.email, employer)
        and (await _user_verified_email_count(db, employee_id)) <= 1
    )

    return {
        "message": f"Successfully linked to {employer.company_name}",
        "company_name": employer.company_name,
        "employer_id": invite.employer_profile_id,
        "needs_personal_email": needs_personal_email,
    }


# =============================================================================
# EMPLOYEE — ACCEPT (public — no existing account)
# =============================================================================

async def accept_invite_new_user(db: AsyncSession, data: AcceptInviteNewUserRequest) -> dict:
    """
    Used when GET /hr/validate returned account_exists: false. Creates a
    brand-new account, links it to the employer, and logs the person in —
    all in one call, since the passport check already confirmed identity.
    This replaces the earlier multi-step "sign up → verify email → set up
    profile → come back to accept" journey with a single form.
    """
    invite = await _resolve_invitation(db, data.invite_token, data.invite_code)
    _check_invite_acceptable(invite)
    _check_passport(invite, data.passport_number)

    normalized_email = data.email.lower().strip()
    existing = await db.scalar(select(User).where(User.email == normalized_email))
    if existing:
        raise ValueError("An account with this email already exists. Try logging in instead.")

    employer_profile_for_check = await db_get_by_id(db, EmployerProfile, invite.employer_profile_id)
    is_domain_email = _matches_employer_domain(normalized_email, employer_profile_for_check)

    user = User(
        first_name=data.first_name, last_name=data.last_name, email=normalized_email,
        password_hash=hash_password(data.password), auth_provider="email",
        is_active=True, is_verified=True,  # passport check already confirmed identity
        terms_accepted=data.terms_accepted,
        terms_accepted_at=datetime.now(timezone.utc) if data.terms_accepted else None,
    )
    user = await db_create(db, user)

    profile = UserProfile(
        user_id=user.id, onboarding_step=1, onboarding_completed=True,
        full_legal_name=f"{data.first_name} {data.last_name}",
        created_by=user.id, modified_by=user.id,
    )
    await db_create(db, profile)

    role_obj = await db.scalar(select(Role).where(Role.name == "employee"))
    if not role_obj:
        raise Exception("RBAC not seeded. Run seed migration first.")
    await db_create(db, UserRole(user_id=user.id, role_id=role_obj.id, assigned_by=user.id, created_by=user.id, modified_by=user.id))

    await _create_verified_user_email(db, user.id, normalized_email, source="work" if is_domain_email else "signup", is_primary=True)

    other_email_added = False
    if data.other_email and data.other_email.lower().strip() != normalized_email:
        await _send_personal_email_verification(db, user.id, data.other_email)
        other_email_added = True

    employer = await _link_employee_to_employer(db, invite, user.id)
    access_token, refresh_token = await _issue_login_tokens(db, user, ["employee"])

    # Domain-matched AND they didn't already add a personal email in this
    # same form — ask once more, right after joining, instead of letting
    # the optional field's being skipped mean they never get asked at all.
    needs_personal_email = is_domain_email and not other_email_added

    return {
        "access_token": access_token, "refresh_token": refresh_token, "roles": ["employee"],
        "company_name": employer.company_name, "employer_id": invite.employer_profile_id,
        "linked_email": data.other_email,
        "needs_personal_email": needs_personal_email,
        "message": f"Welcome to {employer.company_name}! Your account has been created.",
    }


# =============================================================================
# EMPLOYEE — ACCEPT (public — existing account, merge via OTP)
# =============================================================================

async def request_merge_otp(db: AsyncSession, data: RequestMergeOtpRequest) -> dict:
    """
    Step 1 of the merge flow. Used when GET /hr/validate returned
    account_exists: true, but the person opening the invite link isn't
    currently logged in (so we can't just use their session). Sends a
    one-time code to the matched account's email to confirm it's really
    them before merging the new employer link into that account.
    """
    invite = await _resolve_invitation(db, data.invite_token, data.invite_code)
    _check_invite_acceptable(invite)

    user = await _find_user_by_any_email(db, data.login_email)
    if not user:
        raise ValueError("No account found with that email.")

    otp_code = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=MERGE_OTP_EXPIRE_MINUTES)

    await db_create(db, UserOTP(
        user_id=user.id, otp_code=otp_code, otp_type="merge_invite",
        is_used=False, expires_at=expires_at, created_by=user.id,
    ))

    await send_email(
        to=data.login_email,
        subject="Your Vyuflo verification code",
        body=(
            f"Your verification code is: {otp_code}\n\n"
            f"It expires in {MERGE_OTP_EXPIRE_MINUTES} minutes. "
            "Enter this code to confirm it's you and link this invitation to your account."
        ),
    )
    return {"message": "Verification code sent to your email."}


async def accept_invite_existing_user(db: AsyncSession, data: AcceptInviteExistingUserRequest) -> dict:
    """
    Step 2 of the merge flow. Confirms the OTP from request_merge_otp,
    then links the invite to the matched account exactly like the
    authenticated accept path, and logs the person in.
    """
    invite = await _resolve_invitation(db, data.invite_token, data.invite_code)
    _check_invite_acceptable(invite)

    user = await _find_user_by_any_email(db, data.login_email)
    if not user:
        raise ValueError("No account found with that email.")

    otp_result = await db.execute(
        select(UserOTP).where(
            UserOTP.user_id == user.id, UserOTP.otp_code == data.otp_code,
            UserOTP.otp_type == "merge_invite", UserOTP.is_used == False,
        ).order_by(UserOTP.created_at.desc()).limit(1)
    )
    otp = otp_result.scalars().first()
    if not otp or otp.expires_at < datetime.now(timezone.utc):
        raise ValueError("Invalid or expired verification code. Please request a new one.")

    await db_update(db, UserOTP, otp.id, {"is_used": True})

    _check_passport(invite, data.passport_number)

    employer = await _link_employee_to_employer(db, invite, user.id)

    other_email_added = False
    if data.other_email and data.other_email.lower().strip() != user.email.lower().strip():
        try:
            await _send_personal_email_verification(db, user.id, data.other_email)
            other_email_added = True
        except ValueError:
            pass  # already in use elsewhere — don't block acceptance over this

    roles_result = await db.execute(
        select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user.id)
    )
    roles = [r for r, in roles_result.all()] or ["employee"]

    access_token, refresh_token = await _issue_login_tokens(db, user, roles)

    # Same domain-match check as the new-user path — an EXISTING account
    # can still be domain-email-only if they'd never added a backup before.
    is_domain_email = _matches_employer_domain(user.email, employer)
    needs_personal_email = (
        is_domain_email and not other_email_added
        and (await _user_verified_email_count(db, user.id)) <= 1
    )

    return {
        "access_token": access_token, "refresh_token": refresh_token, "roles": roles,
        "company_name": employer.company_name, "employer_id": invite.employer_profile_id,
        "linked_email": data.other_email,
        "needs_personal_email": needs_personal_email,
        "message": f"Successfully linked to {employer.company_name}.",
    }


# =============================================================================
# HR — MANAGE EMPLOYEES
# =============================================================================

async def get_my_employees(db, hr_user_id, is_active=True, limit=50, offset=0):
    employer = await _get_employer_profile(db, hr_user_id)
    if not employer:
        return [], 0
    filters = [EmployerEmployee.employer_id == hr_user_id]
    if is_active is not None:
        filters.append(EmployerEmployee.is_active == is_active)
    count_result = await db.execute(select(func.count()).select_from(EmployerEmployee).where(*filters))
    total = count_result.scalar() or 0
    result = await db.execute(
        select(EmployerEmployee).where(*filters).order_by(EmployerEmployee.created_at.desc()).limit(limit).offset(offset)
    )
    employee_links = result.scalars().all()

    employees = []
    for link in employee_links:
        emp_user = await db_get_by_id(db, User, link.employee_id)
        emp_profile_result = await db.execute(select(UserProfile).where(UserProfile.user_id == link.employee_id))
        emp_profile = emp_profile_result.scalars().first()

        app_count_result = await db.execute(
            select(func.count()).select_from(Application).where(
                Application.user_id == link.employee_id, Application.assigned_hr_id == hr_user_id,
                Application.status.in_(["draft", "in_progress", "action_needed", "submitted", "rfe_response"]),
            )
        )
        active_apps = app_count_result.scalar() or 0

        if emp_user:
            full_name = emp_profile.full_legal_name if emp_profile and emp_profile.full_legal_name \
                else f"{emp_user.first_name} {emp_user.last_name}".strip()
            employees.append({
                "id": link.id, "employee_id": link.employee_id, "full_name": full_name,
                "email": emp_user.email, "profile_picture_url": emp_profile.profile_picture_url if emp_profile else None,
                "job_title": link.job_title, "department": link.department, "work_email": link.work_email,
                "start_date": str(link.start_date) if link.start_date else None, "is_active": link.is_active,
                "access_revoked_at": link.access_revoked_at.isoformat() if link.access_revoked_at else None,
                "active_applications": active_apps, "pending_documents": 0, "linked_at": link.created_at,
            })
    return employees, total


async def update_employee_info(db, hr_user_id, employee_link_id, data: UpdateEmployeeRequest):
    link = await db_get_by_id(db, EmployerEmployee, employee_link_id)
    if not link:
        raise ValueError("Employee link not found.")
    if link.employer_id != hr_user_id:
        raise PermissionError("You can only update your own employees.")
    update_data = {k: v for k, v in data.model_dump(exclude_none=True).items()}
    if not update_data:
        return link
    return await db_update(db, EmployerEmployee, employee_link_id, update_data)


async def deactivate_employee(db, hr_user_id, employee_link_id):
    link = await db_get_by_id(db, EmployerEmployee, employee_link_id)
    if not link:
        raise ValueError("Employee link not found.")
    if link.employer_id != hr_user_id:
        raise PermissionError("You can only remove your own employees.")
    now = datetime.now(timezone.utc)
    grace_end = now + timedelta(days=OFFBOARDING_GRACE_PERIOD_DAYS)
    return await db_update(db, EmployerEmployee, employee_link_id, {
        "end_date": now.date(), "access_revoked_at": grace_end,
    })


async def get_employee_detail(db, hr_user_id, employee_link_id):
    link = await db_get_by_id(db, EmployerEmployee, employee_link_id)
    if not link:
        raise ValueError("Employee link not found.")
    if link.employer_id != hr_user_id:
        raise PermissionError("You can only view your own employees.")

    emp_user = await db_get_by_id(db, User, link.employee_id)
    emp_profile_result = await db.execute(select(UserProfile).where(UserProfile.user_id == link.employee_id))
    emp_profile = emp_profile_result.scalars().first()
    employer = await _get_employer_profile(db, hr_user_id)

    full_name = (emp_profile.full_legal_name if emp_profile and emp_profile.full_legal_name
                 else f"{emp_user.first_name} {emp_user.last_name}".strip() if emp_user else "Unknown")

    apps_result = await db.execute(select(Application).where(Application.user_id == link.employee_id).order_by(Application.created_at.desc()))
    all_apps = apps_result.scalars().all()
    active_statuses = {"in_progress", "action_needed", "rfe_response", "submitted"}
    active_apps = [a for a in all_apps if a.status in active_statuses]
    primary_case = active_apps[0] if active_apps else None

    async def _build_app_summary(app):
        vt_result = await db.execute(select(VisaType).where(VisaType.id == app.visa_type_id))
        vt = vt_result.scalars().first()
        attorney = await db_get_by_id(db, User, app.assigned_attorney_id) if app.assigned_attorney_id else None
        history_result = await db.execute(
            select(ApplicationStatusHistory).where(ApplicationStatusHistory.application_id == app.id)
            .order_by(ApplicationStatusHistory.created_at.desc()).limit(1)
        )
        latest_history = history_result.scalars().first()
        return {
            "id": str(app.id), "application_number": app.application_number,
            "visa_type_code": vt.code if vt else "—", "visa_type_name": f"{vt.code} Extension" if vt else "Unknown",
            "status": app.status, "current_stage": app.current_stage, "progress_percent": app.progress_percent,
            "start_date": str(app.start_date) if app.start_date else None, "due_date": str(app.due_date) if app.due_date else None,
            "next_milestone": latest_history.stage.replace("_", " ").title() if latest_history else None,
            "assigned_attorney_name": f"{attorney.first_name} {attorney.last_name}".strip() if attorney else None,
            "assigned_attorney_avatar": None,
        }

    all_cases_summary = [await _build_app_summary(a) for a in all_apps]
    active_case_summary = await _build_app_summary(primary_case) if primary_case else None

    from app.models.visamodels import Document
    from sqlalchemy.orm import joinedload
    docs_result = await db.execute(
        select(Document).options(joinedload(Document.document_type))
        .where(Document.user_id == link.employee_id).order_by(Document.updated_at.desc()).limit(12)
    )
    docs = docs_result.unique().scalars().all()
    documents_summary = [{
        "id": str(doc.id), "name": doc.document_type.name if doc.document_type else doc.file_name,
        "status": doc.status, "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
        "file_format": doc.file_format,
    } for doc in docs]

    from app.models.visamodels import Deadline
    verified_docs = sum(1 for d in docs if d.status == "verified")
    deadline_result = await db.execute(
        select(Deadline).where(
            Deadline.user_id == link.employee_id, Deadline.is_completed == False,
            Deadline.is_dismissed == False, Deadline.due_date >= datetime.now(timezone.utc),
        ).order_by(Deadline.due_date.asc()).limit(1)
    )
    next_deadline = deadline_result.scalars().first()
    next_deadline_days = max(0, (next_deadline.due_date - datetime.now(timezone.utc)).days) if next_deadline else None

    stats = {
        "active_cases": len(active_apps), "total_cases": len(all_apps),
        "documents_total": len(docs), "documents_verified": verified_docs,
        "next_deadline_days": next_deadline_days,
    }

    history_result = await db.execute(
        select(ApplicationStatusHistory).where(ApplicationStatusHistory.application_id.in_([a.id for a in all_apps]))
        .order_by(ApplicationStatusHistory.created_at.desc()).limit(10)
    )
    history_items = history_result.scalars().all()
    dot_map = {"approved": "green", "submitted": "blue", "action_needed": "orange", "rfe_response": "orange",
               "in_progress": "blue", "draft": "gray", "rejected": "gray", "withdrawn": "gray"}
    activity = []
    for h in history_items:
        actor_user = await db_get_by_id(db, User, h.changed_by) if h.changed_by else None
        actor_label = f"{actor_user.first_name} {actor_user.last_name}".strip() if actor_user else "System"
        activity.append({
            "id": str(h.id), "title": f"{h.status.replace('_', ' ').title()} — {h.stage.replace('_', ' ').title()}",
            "actor": f"By {actor_label}", "occurred_at": h.created_at.isoformat(), "dot_color": dot_map.get(h.status, "gray"),
        })

    visa_code = None
    if all_apps:
        latest_vt_result = await db.execute(select(VisaType).where(VisaType.id == all_apps[0].visa_type_id))
        latest_vt = latest_vt_result.scalars().first()
        if latest_vt:
            visa_code = latest_vt.code

    return {
        "profile": {
            "employee_link_id": str(link.id), "user_id": str(link.employee_id), "full_name": full_name,
            "email": emp_user.email if emp_user else "", "profile_picture_url": emp_profile.profile_picture_url if emp_profile else None,
            "job_title": link.job_title, "department": link.department, "work_email": link.work_email,
            "start_date": str(link.start_date) if link.start_date else None,
            "company_name": employer.company_name if employer else None,
            "company_location": f"{employer.city}, {employer.state}".strip(", ") if employer and employer.city else None,
            "visa_code": visa_code, "visa_status_label": "Active" if active_apps else "No Active Visa",
            "linked_at": link.created_at.isoformat(), "is_active": link.is_active,
        },
        "stats": stats, "active_case": active_case_summary, "all_cases": all_cases_summary,
        "documents": documents_summary, "activity": activity,
    }