# app/services/invitation_service.py
import uuid
import secrets
import string
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.visamodels import (
    ApplicationStatusHistory,
    EmployerInvitation,
    EmployerEmployee,
    EmployerProfile,
    PasswordResetToken,
    UserProfile,
    User,
    UserRole,
    Role,
    Application,
    VisaType,
)

from app.schemas.hr.invitation_schemas import (
    InviteByEmailRequest,
    InviteByCodeRequest,
    InviteByLinkRequest,
    AcceptInviteRequest,
    AcceptInviteNewUserRequest,
    AcceptInviteExistingUserRequest,
    UpdateEmployeeRequest,
)
from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.services.employee.message_service import get_or_create_thread_for_participants
from app.services.employee.services import (
    _store_refresh_token,
    db_create,
    db_get_by_id,
    db_update,
)


# =============================================================================
# HELPERS
# =============================================================================

def _generate_invite_code() -> str:
    """Generate short human-readable code: VF-XXXX-XXXX"""
    chars = string.ascii_uppercase + string.digits
    part1 = ''.join(secrets.choice(chars) for _ in range(4))
    part2 = ''.join(secrets.choice(chars) for _ in range(4))
    return f"VF-{part1}-{part2}"


def _generate_invite_token() -> str:
    """Generate long URL-safe token for link invites."""
    return secrets.token_urlsafe(48)


async def _get_employer_profile(
    db: AsyncSession,
    hr_user_id: uuid.UUID,
) -> Optional[EmployerProfile]:
    """Get the EmployerProfile for the current HR user."""
    result = await db.execute(
        select(EmployerProfile).where(EmployerProfile.user_id == hr_user_id)
    )
    return result.scalars().first()


async def _find_existing_user_for_email(
    db: AsyncSession,
    email: str,
) -> Optional[User]:
    """
    Used to answer "does this person already have an account?" when a
    company invite comes in for `email`.

    Matches against BOTH:
    - User.personal_email (the true identity, once a user has added one)
    - User.email           (covers users who signed up the normal way and
                             never got a personal_email split out yet)

    This is intentionally NOT scoped to a single employer — the whole point
    is to catch the same person coming back under a DIFFERENT employer.
    """
    email = email.lower().strip()
    result = await db.execute(
        select(User).where(
            (User.personal_email == email) | (User.email == email)
        )
    )
    return result.scalars().first()


async def _link_employee_to_employer(
    db: AsyncSession,
    *,
    invite: EmployerInvitation,
    employer: EmployerProfile,
    employee_id: uuid.UUID,
    work_email: Optional[str],
) -> None:
    """
    Shared "attach this employee to this employer" logic — used by:
    - accept_invite            (already-logged-in employee, code/link invite)
    - accept_invite_new_user   (brand new account created from a company invite)
    - accept_invite_existing_user (merge into a pre-existing account)

    Does NOT touch User.personal_email / User.email — those are decided by
    the caller depending on which of the three scenarios above we're in.
    """
    now = datetime.now(timezone.utc)

    # ── Create employer_employees record ──────────────────────────────────
    link = EmployerEmployee(
        employer_id         = invite.created_by,
        employee_id         = employee_id,
        employer_profile_id = invite.employer_profile_id,
        invitation_id        = invite.id,
        is_active            = True,
        work_email           = work_email,
        created_by           = employee_id,
    )
    await db_create(db, link)

    # ── Update user_profiles.employer_id ───────────────────────────────────
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == employee_id)
    )
    profile = profile_result.scalars().first()
    if profile:
        await db_update(db, UserProfile, profile.id, {
            "employer_id": invite.employer_profile_id,
            "invited_by":  invite.created_by,
        })

    # ── Update invite status ────────────────────────────────────────────────
    if invite.max_uses and invite.max_uses == 1:
        await db_update(db, EmployerInvitation, invite.id, {
            "status":      "accepted",
            "accepted_by": employee_id,
            "accepted_at": now,
            "used_count":  invite.used_count + 1,
        })
    else:
        await db_update(db, EmployerInvitation, invite.id, {
            "used_count":  invite.used_count + 1,
            "accepted_by": employee_id,
            "accepted_at": now,
        })

    # ── Auto-assign HR to existing applications ────────────────────────────
    await db.execute(
        Application.__table__.update()
        .where(
            Application.user_id        == employee_id,
            Application.assigned_hr_id == None,
        )
        .values(assigned_hr_id=invite.created_by)
    )

    # ── Auto-create direct HR ↔ employee conversation ──────────────────────
    hr_user = await db_get_by_id(db, User, invite.created_by)
    hr_name = (
        f"{hr_user.first_name} {hr_user.last_name}".strip()
        if hr_user else "HR"
    )
    await get_or_create_thread_for_participants(
        db              = db,
        actor_id        = invite.created_by,
        participant_ids = [employee_id],
        thread_type     = "direct",
        initial_message = (
            f"Hi! I'm {hr_name} from {employer.company_name}. "
            "Welcome to Vyuflo — I'll be your HR contact for your immigration case. "
            "Feel free to reach out here with any questions."
        ),
    )


async def _validate_invite_object(invite: Optional[EmployerInvitation]) -> None:
    """Raises ValueError with a user-facing message if the invite can't be used."""
    if not invite:
        raise ValueError("Invalid invite code or link.")
    if invite.status == "revoked":
        raise ValueError("This invitation has been revoked.")
    if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
        raise ValueError("This invitation has expired.")
    if invite.max_uses and invite.used_count >= invite.max_uses:
        raise ValueError("This invite has reached its maximum uses.")


async def _resolve_invitation(
    db: AsyncSession,
    invite_token: Optional[str],
    invite_code: Optional[str],
) -> Optional[EmployerInvitation]:
    """Find an invitation by token or code."""
    if invite_token:
        result = await db.execute(
            select(EmployerInvitation).where(
                EmployerInvitation.invite_token == invite_token
            )
        )
        return result.scalars().first()
    if invite_code:
        result = await db.execute(
            select(EmployerInvitation).where(
                EmployerInvitation.invite_code == invite_code.upper().strip()
            )
        )
        return result.scalars().first()
    return None


# =============================================================================
# HR — CREATE INVITATIONS
# =============================================================================

async def create_email_invite(
    db:         AsyncSession,
    hr_user_id: uuid.UUID,
    data:       InviteByEmailRequest,
) -> EmployerInvitation:
    """
    HR invites a specific employee by email.
    System sends an email with a unique token link.
    """
    employer = await _get_employer_profile(db, hr_user_id)
    if not employer:
        raise ValueError("Employer profile not found. Complete your company setup first.")

    # Check if this email already has a pending invite from this company
    existing = await db.execute(
        select(EmployerInvitation).where(
            EmployerInvitation.employer_profile_id == employer.id,
            EmployerInvitation.invited_email       == data.email,
            EmployerInvitation.status              == "pending",
        )
    )
    if existing.scalars().first():
        raise ValueError(f"A pending invite already exists for {data.email}. Revoke it first.")

    token = _generate_invite_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_days)

    invite = EmployerInvitation(
        created_by          = hr_user_id,
        employer_profile_id = employer.id,
        invite_method       = "email",
        invited_email       = data.email.lower().strip(),
        invite_token        = token,
        max_uses            = 1,   # email invite = single use
        status              = "pending",
        expires_at          = expires_at,
        personal_message    = data.personal_message,
    )
    return await db_create(db, invite)


async def create_code_invite(
    db:         AsyncSession,
    hr_user_id: uuid.UUID,
    data:       InviteByCodeRequest,
) -> EmployerInvitation:
    """
    HR generates a reusable company code.
    HR shares this code offline (offer letter, WhatsApp, Slack).
    Employee enters code on Vyuflo to connect.
    """
    employer = await _get_employer_profile(db, hr_user_id)
    if not employer:
        raise ValueError("Employer profile not found.")

    # Generate unique code — retry if collision
    for _ in range(5):
        code = _generate_invite_code()
        existing = await db.execute(
            select(EmployerInvitation).where(
                EmployerInvitation.invite_code == code
            )
        )
        if not existing.scalars().first():
            break
    else:
        raise ValueError("Could not generate unique code. Try again.")

    invite = EmployerInvitation(
        created_by          = hr_user_id,
        employer_profile_id = employer.id,
        invite_method       = "code",
        invite_code         = code,
        max_uses            = data.max_uses,      # None = unlimited
        status              = "pending",
        expires_at          = None,               # codes don't expire by default
        personal_message    = data.personal_message,
    )
    return await db_create(db, invite)


async def create_link_invite(
    db:         AsyncSession,
    hr_user_id: uuid.UUID,
    data:       InviteByLinkRequest,
) -> EmployerInvitation:
    """
    HR generates a shareable link.
    Anyone with the link can join (up to max_uses).
    """
    employer = await _get_employer_profile(db, hr_user_id)
    if not employer:
        raise ValueError("Employer profile not found.")

    token = _generate_invite_token()
    expires_at = None
    if data.expires_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_days)

    invite = EmployerInvitation(
        created_by          = hr_user_id,
        employer_profile_id = employer.id,
        invite_method       = "link",
        invite_token        = token,
        max_uses            = data.max_uses,
        status              = "pending",
        expires_at          = expires_at,
        personal_message    = data.personal_message,
    )
    return await db_create(db, invite)


# =============================================================================
# HR — MANAGE INVITATIONS
# =============================================================================

async def get_my_invitations(
    db:         AsyncSession,
    hr_user_id: uuid.UUID,
    status:     Optional[str] = None,
    limit:      int = 50,
    offset:     int = 0,
) -> tuple[list[EmployerInvitation], int]:
    """HR lists all invitations they sent."""
    employer = await _get_employer_profile(db, hr_user_id)
    if not employer:
        return [], 0

    filters = [EmployerInvitation.employer_profile_id == employer.id]
    if status:
        filters.append(EmployerInvitation.status == status)

    # Total count
    count_result = await db.execute(
        select(func.count()).select_from(EmployerInvitation).where(*filters)
    )
    total = count_result.scalar() or 0

    # Items
    result = await db.execute(
        select(EmployerInvitation)
        .where(*filters)
        .order_by(EmployerInvitation.created_at.desc())
        .limit(limit).offset(offset)
    )
    return result.scalars().all(), total


async def revoke_invitation(
    db:            AsyncSession,
    hr_user_id:    uuid.UUID,
    invitation_id: uuid.UUID,
) -> EmployerInvitation:
    """HR revokes a pending invitation."""
    invite = await db_get_by_id(db, EmployerInvitation, invitation_id)
    if not invite:
        raise ValueError("Invitation not found.")
    if invite.created_by != hr_user_id:
        raise PermissionError("You can only revoke your own invitations.")
    if invite.status != "pending":
        raise ValueError(f"Cannot revoke a '{invite.status}' invitation.")

    return await db_update(db, EmployerInvitation, invitation_id, {
        "status":     "revoked",
        "revoked_by": hr_user_id,
        "revoked_at": datetime.now(timezone.utc),
    })


async def resend_email_invite(
    db:            AsyncSession,
    hr_user_id:    uuid.UUID,
    invitation_id: uuid.UUID,
) -> EmployerInvitation:
    """
    HR resends an email invite — generates a fresh token,
    resets expiry to 7 days from now.
    """
    invite = await db_get_by_id(db, EmployerInvitation, invitation_id)
    if not invite:
        raise ValueError("Invitation not found.")
    if invite.created_by != hr_user_id:
        raise PermissionError("You can only resend your own invitations.")
    if invite.invite_method != "email":
        raise ValueError("Only email invites can be resent.")

    new_token  = _generate_invite_token()
    new_expiry = datetime.now(timezone.utc) + timedelta(days=7)

    return await db_update(db, EmployerInvitation, invitation_id, {
        "invite_token": new_token,
        "expires_at":   new_expiry,
        "status":       "pending",
    })


# =============================================================================
# EMPLOYEE — VALIDATE & ACCEPT INVITATION
# =============================================================================

async def validate_invite(
    db:           AsyncSession,
    invite_token: Optional[str],
    invite_code:  Optional[str],
) -> dict:
    """
    Public endpoint — employee checks if token/code is valid
    BEFORE showing the accept page.
    Returns company name + HR name so employee can confirm.
    """
    invite = await _resolve_invitation(db, invite_token, invite_code)

    if not invite:
        return {"valid": False, "message": "Invalid invite code or link."}

    if invite.status == "revoked":
        return {"valid": False, "message": "This invitation has been revoked."}

    if invite.status == "expired":
        return {"valid": False, "message": "This invitation has expired."}

    if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
        # Auto-expire
        await db_update(db, EmployerInvitation, invite.id, {"status": "expired"})
        return {"valid": False, "message": "This invitation has expired."}

    if invite.max_uses and invite.used_count >= invite.max_uses:
        return {"valid": False, "message": "This invite has reached its maximum uses."}

    if invite.status not in ("pending",):
        return {"valid": False, "message": "This invitation is no longer valid."}

    # Get company + HR info
    employer = await db_get_by_id(db, EmployerProfile, invite.employer_profile_id)
    hr_user  = await db_get_by_id(db, User, invite.created_by)
    hr_name  = f"{hr_user.first_name} {hr_user.last_name}".strip() if hr_user else "HR Team"

    # Does someone already own this email (personal_email OR login email)?
    # Drives whether the frontend shows a "log in" or "sign up" screen next.
    account_exists = False
    if invite.invited_email:
        existing = await _find_existing_user_for_email(db, invite.invited_email)
        account_exists = existing is not None

    return {
        "valid":          True,
        "company_name":   employer.company_name if employer else "Unknown Company",
        "hr_name":        hr_name,
        "invite_method":  invite.invite_method,
        "message":        f"Valid invite from {employer.company_name if employer else 'a company'}",
        "account_exists": account_exists,
    }


async def accept_invite(
    db:          AsyncSession,
    employee_id: uuid.UUID,
    data:        AcceptInviteRequest,
) -> dict:
    """
    Employee accepts an invitation.
    This is the KEY action that links the employee to the employer.

    What happens:
    1. Validate the invite
    2. Create employer_employees row
    3. Update user_profiles.employer_id
    4. Mark invite as accepted / increment used_count
    5. Auto-set assigned_hr_id on any existing applications
    """
    invite = await _resolve_invitation(db, data.invite_token, data.invite_code)

    if not invite:
        raise ValueError("Invalid invite code or link.")

    # Validate
    if invite.status == "revoked":
        raise ValueError("This invitation has been revoked.")
    if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
        await db_update(db, EmployerInvitation, invite.id, {"status": "expired"})
        raise ValueError("This invitation has expired.")
    if invite.max_uses and invite.used_count >= invite.max_uses:
        raise ValueError("This invite has reached its maximum uses.")

    # Check employee not already linked to this company
    existing_link = await db.execute(
        select(EmployerEmployee).where(
            EmployerEmployee.employee_id         == employee_id,
            EmployerEmployee.employer_profile_id == invite.employer_profile_id,
            EmployerEmployee.is_active           == True,
        )
    )
    if existing_link.scalars().first():
        raise ValueError("You are already linked to this company.")

    employer = await db_get_by_id(db, EmployerProfile, invite.employer_profile_id)
    if not employer:
        raise ValueError("Company not found.")

    await _link_employee_to_employer(
        db,
        invite       = invite,
        employer     = employer,
        employee_id  = employee_id,
        work_email   = invite.invited_email,
    )

    return {
        "message":      f"Successfully linked to {employer.company_name}",
        "company_name": employer.company_name,
        "employer_id":  invite.employer_profile_id,
    }


# =============================================================================
# EMPLOYEE — ACCEPT INVITE (PUBLIC, NOT-YET-AUTHENTICATED FLOWS)
# =============================================================================
#
# These two cover your manager's actual requirement:
#
#   accept_invite_existing_user  → "user already has an account" → MERGE
#   accept_invite_new_user       → "user has no account"         → CREATE,
#                                    then ask for personal email
#
# In both cases `personal_email` ends up being the long-term primary
# identifier — new accounts are flagged `requires_personal_email=True`
# until they add one.
# =============================================================================

async def accept_invite_existing_user(
    db:   AsyncSession,
    data: AcceptInviteExistingUserRequest,
) -> dict:
    """
    Scenario 1 — employee already has an account.
    They prove it's them by logging in (email + password) or via a verified
    forgot-password OTP token, then we attach the new employer link to their
    EXISTING account. Old data (documents, applications, previous cases,
    etc.) stays exactly where it is — nothing is duplicated.
    """
    invite = await _resolve_invitation(db, data.invite_token, data.invite_code)
    await _validate_invite_object(invite)

    employer = await db_get_by_id(db, EmployerProfile, invite.employer_profile_id)
    if not employer:
        raise ValueError("Company not found.")

    # ── Confirm identity ────────────────────────────────────────────────────
    login_email = data.login_email.lower().strip()
    result = await db.execute(
        select(User).where(
            (User.personal_email == login_email) | (User.email == login_email)
        )
    )
    user = result.scalars().first()
    if not user:
        raise UnauthorizedException("Incorrect email or password.")

    identity_confirmed = False
    reset_token = None

    if data.password:
        identity_confirmed = bool(
            user.password_hash and verify_password(data.password, user.password_hash)
        )
    elif data.reset_token_id:
        # "Forgot password?" path — they already completed request → OTP →
        # verify against this same email, so a VERIFIED token for THIS user
        # is proof enough. No separate password change required here.
        reset_token = await db_get_by_id(db, PasswordResetToken, uuid.UUID(data.reset_token_id))
        identity_confirmed = bool(
            reset_token
            and reset_token.status == "verified"
            and reset_token.user_id == user.id
        )

    if not identity_confirmed:
        raise UnauthorizedException("Incorrect email or password.")

    if reset_token:
        # Consume it — a verified reset token should only unlock one action.
        await db_update(db, PasswordResetToken, reset_token.id, {"status": "completed"})

        # If they set a new password in the same step, apply it now — avoids
        # leaving them stuck re-doing "forgot password" on their next login.
        if data.new_password:
            await db_update(db, User, user.id, {"password_hash": hash_password(data.new_password)})

    # ── Already linked to this employer? ───────────────────────────────────
    existing_link = await db.execute(
        select(EmployerEmployee).where(
            EmployerEmployee.employee_id         == user.id,
            EmployerEmployee.employer_profile_id == invite.employer_profile_id,
            EmployerEmployee.is_active           == True,
        )
    )
    if existing_link.scalars().first():
        raise ValueError("You are already linked to this company.")

    # ── Merge: attach invite to the EXISTING user, personal_email untouched ─
    await _link_employee_to_employer(
        db,
        invite      = invite,
        employer    = employer,
        employee_id = user.id,
        work_email  = invite.invited_email,
    )

    role_result = await db.execute(
        select(Role.name).join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
    )
    roles = [r for (r,) in role_result.all()] or ["employee"]

    access_token  = create_access_token(str(user.id), roles, user.email, user.first_name or "", user.last_name or "")
    refresh_token = create_refresh_token(str(user.id))
    await _store_refresh_token(str(user.id), refresh_token)

    return {
        "access_token":            access_token,
        "refresh_token":           refresh_token,
        "roles":                   roles,
        "company_name":            employer.company_name,
        "employer_id":             invite.employer_profile_id,
        "requires_personal_email": user.requires_personal_email,
        "message":                 f"Welcome back! Your account is now linked to {employer.company_name}.",
    }


async def accept_invite_new_user(
    db:   AsyncSession,
    data: AcceptInviteNewUserRequest,
) -> dict:
    """
    Scenario 2 — no existing account for this email.
    Creates a fresh account using the COMPANY email (invite.invited_email).
    `personal_email` is left NULL and `requires_personal_email=True` — the
    frontend must show a "please add your personal email" step right after
    this call succeeds, since company email should never be treated as the
    long-term primary identifier.
    """
    invite = await _resolve_invitation(db, data.invite_token, data.invite_code)
    await _validate_invite_object(invite)

    if not invite.invited_email:
        raise ValueError("This invite type doesn't support account creation directly.")

    employer = await db_get_by_id(db, EmployerProfile, invite.employer_profile_id)
    if not employer:
        raise ValueError("Company not found.")

    company_email = invite.invited_email.lower().strip()

    # Guard against a race: someone may have signed up with this exact email
    # between validate_invite() and this call.
    existing = await _find_existing_user_for_email(db, company_email)
    if existing:
        raise ConflictException(
            "An account already exists for this email. Please log in instead."
        )

    # ── Create User (company email as login, personal_email left NULL) ─────
    user = User(
        first_name              = data.first_name,
        last_name               = data.last_name,
        email                   = company_email,
        personal_email          = None,
        requires_personal_email = True,
        password_hash           = hash_password(data.password),
        auth_provider           = "email",
        is_active               = True,
        is_verified             = True,   # employer already vouched for this email
        terms_accepted          = data.terms_accepted,
        terms_accepted_at       = datetime.now(timezone.utc) if data.terms_accepted else None,
    )
    user = await db_create(db, user)

    profile = UserProfile(
        user_id         = user.id,
        onboarding_step = 1,
        full_legal_name = f"{data.first_name} {data.last_name}",
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

    # ── Link to employer (work_email = the company email they were invited on) ─
    await _link_employee_to_employer(
        db,
        invite      = invite,
        employer    = employer,
        employee_id = user.id,
        work_email  = company_email,
    )

    access_token  = create_access_token(str(user.id), ["employee"], user.email, user.first_name, user.last_name)
    refresh_token = create_refresh_token(str(user.id))
    await _store_refresh_token(str(user.id), refresh_token)

    return {
        "access_token":            access_token,
        "refresh_token":           refresh_token,
        "roles":                   ["employee"],
        "company_name":            employer.company_name,
        "employer_id":             invite.employer_profile_id,
        "requires_personal_email": True,
        "message":                 f"Account created and linked to {employer.company_name}. "
                                    "Please add your personal email to finish setting up your account.",
    }


async def add_personal_email(
    db:      AsyncSession,
    user_id: uuid.UUID,
    email:   str,
) -> dict:
    """
    Lets a user set/update their personal (primary) email — this is the step
    that follows accept_invite_new_user, but can also be used any time a
    user wants to add one proactively.
    """
    email = email.lower().strip()

    existing = await _find_existing_user_for_email(db, email)
    if existing and existing.id != user_id:
        raise ConflictException("This email is already used by another account.")

    await db_update(db, User, user_id, {
        "personal_email":          email,
        "requires_personal_email": False,
    })
    return {"message": "Personal email added.", "personal_email": email}


# =============================================================================
# HR — MANAGE EMPLOYEES
# =============================================================================

async def get_my_employees(
    db:         AsyncSession,
    hr_user_id: uuid.UUID,
    is_active:  Optional[bool] = True,
    limit:      int = 50,
    offset:     int = 0,
) -> tuple[list[dict], int]:
    """
    HR lists all employees linked to their company.
    Includes application stats per employee.
    """
    employer = await _get_employer_profile(db, hr_user_id)
    if not employer:
        return [], 0

    filters = [EmployerEmployee.employer_id == hr_user_id]
    if is_active is not None:
        filters.append(EmployerEmployee.is_active == is_active)

    count_result = await db.execute(
        select(func.count()).select_from(EmployerEmployee).where(*filters)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(EmployerEmployee)
        .where(*filters)
        .order_by(EmployerEmployee.created_at.desc())
        .limit(limit).offset(offset)
    )
    employee_links = result.scalars().all()

    # Build response with employee info
    employees = []
    for link in employee_links:
        emp_user = await db_get_by_id(db, User, link.employee_id)
        emp_profile_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == link.employee_id)
        )
        emp_profile = emp_profile_result.scalars().first()

        # Count active applications
        app_count_result = await db.execute(
            select(func.count()).select_from(Application).where(
                Application.user_id        == link.employee_id,
                Application.assigned_hr_id == hr_user_id,
                Application.status.in_(["draft", "in_progress", "action_needed",
                                        "submitted", "rfe_response"]),
            )
        )
        active_apps = app_count_result.scalar() or 0

        if emp_user:
            full_name = emp_profile.full_legal_name if emp_profile and emp_profile.full_legal_name \
                        else f"{emp_user.first_name} {emp_user.last_name}".strip()

            employees.append({
                "id":                  link.id,
                "employee_id":         link.employee_id,
                "full_name":           full_name,
                "email":               emp_user.email,
                "profile_picture_url": emp_profile.profile_picture_url if emp_profile else None,
                "job_title":           link.job_title,
                "department":          link.department,
                "work_email":          link.work_email,
                "start_date":          str(link.start_date) if link.start_date else None,
                "is_active":           link.is_active,
                "active_applications": active_apps,
                "pending_documents":   0,  # can be extended
                "linked_at":           link.created_at,
            })

    return employees, total


async def update_employee_info(
    db:            AsyncSession,
    hr_user_id:    uuid.UUID,
    employee_link_id: uuid.UUID,
    data:          UpdateEmployeeRequest,
) -> EmployerEmployee:
    """HR updates job info for a linked employee."""
    link = await db_get_by_id(db, EmployerEmployee, employee_link_id)
    if not link:
        raise ValueError("Employee link not found.")
    if link.employer_id != hr_user_id:
        raise PermissionError("You can only update your own employees.")

    update_data = {k: v for k, v in data.model_dump(exclude_none=True).items()}
    if not update_data:
        return link

    return await db_update(db, EmployerEmployee, employee_link_id, update_data)


async def deactivate_employee(
    db:               AsyncSession,
    hr_user_id:       uuid.UUID,
    employee_link_id: uuid.UUID,
) -> EmployerEmployee:
    """HR deactivates (removes) an employee from their company."""
    link = await db_get_by_id(db, EmployerEmployee, employee_link_id)
    if not link:
        raise ValueError("Employee link not found.")
    if link.employer_id != hr_user_id:
        raise PermissionError("You can only remove your own employees.")

    return await db_update(db, EmployerEmployee, employee_link_id, {
        "is_active": False,
        "end_date":  datetime.now(timezone.utc).date(),
    })


async def get_employee_detail(
    db:               AsyncSession,
    hr_user_id:       uuid.UUID,
    employee_link_id: uuid.UUID,
) -> dict:
    """
    Returns the full payload for Screen 21 (HR Employee Profile Detail).
    Aggregates:
      - profile info from employer_employees + user + user_profiles
      - stats (active/total cases, documents, next deadline)
      - active case (most recent in_progress/action_needed application)
      - all cases (full list)
      - documents (most recent 12)
      - activity (most recent 10 from application_status_history + document_activity)
    """
    # ── 1. Fetch the employee link ────────────────────────────────────────────
    link = await db_get_by_id(db, EmployerEmployee, employee_link_id)
    if not link:
        raise ValueError("Employee link not found.")
    if link.employer_id != hr_user_id:
        raise PermissionError("You can only view your own employees.")
 
    emp_user    = await db_get_by_id(db, User, link.employee_id)
    emp_profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == link.employee_id)
    )
    emp_profile = emp_profile_result.scalars().first()
 
    employer   = await _get_employer_profile(db, hr_user_id)
 
    full_name = (emp_profile.full_legal_name
                 if emp_profile and emp_profile.full_legal_name
                 else f"{emp_user.first_name} {emp_user.last_name}".strip()
                 if emp_user else "Unknown")
 
    # ── 2. All applications ───────────────────────────────────────────────────
    apps_result = await db.execute(
        select(Application)
        .where(Application.user_id == link.employee_id)
        .order_by(Application.created_at.desc())
    )
    all_apps = apps_result.scalars().all()
 
    active_statuses = {"in_progress", "action_needed", "rfe_response", "submitted"}
    active_apps  = [a for a in all_apps if a.status in active_statuses]
    primary_case = active_apps[0] if active_apps else None
 
    async def _build_app_summary(app: Application) -> dict:
        vt_result = await db.execute(
            select(VisaType).where(VisaType.id == app.visa_type_id)
        )
        vt = vt_result.scalars().first()
 
        attorney = None
        if app.assigned_attorney_id:
            attorney = await db_get_by_id(db, User, app.assigned_attorney_id)
 
        # Get most recent status_history entry for next_milestone
        history_result = await db.execute(
            select(ApplicationStatusHistory)
            .where(ApplicationStatusHistory.application_id == app.id)
            .order_by(ApplicationStatusHistory.created_at.desc())
            .limit(1)
        )
        latest_history = history_result.scalars().first()
 
        return {
            "id":                      str(app.id),
            "application_number":      app.application_number,
            "visa_type_code":          vt.code if vt else "—",
            "visa_type_name":          f"{vt.code} Extension" if vt else "Unknown",
            "status":                  app.status,
            "current_stage":           app.current_stage,
            "progress_percent":        app.progress_percent,
            "start_date":              str(app.start_date) if app.start_date else None,
            "due_date":                str(app.due_date) if app.due_date else None,
            "next_milestone":          latest_history.stage.replace("_", " ").title() if latest_history else None,
            "assigned_attorney_name":  f"{attorney.first_name} {attorney.last_name}".strip() if attorney else None,
            "assigned_attorney_avatar": None,
        }
 
    all_cases_summary = [await _build_app_summary(a) for a in all_apps]
    active_case_summary = await _build_app_summary(primary_case) if primary_case else None
 
    # ── 3. Documents ──────────────────────────────────────────────────────────
    from app.models.visamodels import Document, DocumentType
    from sqlalchemy.orm import joinedload
 
    docs_result = await db.execute(
        select(Document)
        .options(joinedload(Document.document_type))
        .where(Document.user_id == link.employee_id)
        .order_by(Document.updated_at.desc())
        .limit(12)
    )
    docs = docs_result.unique().scalars().all()
 
    documents_summary = []
    for doc in docs:
        doc_name = (doc.document_type.name
                    if doc.document_type else doc.file_name)
        documents_summary.append({
            "id":         str(doc.id),
            "name":       doc_name,
            "status":     doc.status,
            "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
            "file_format": doc.file_format,
        })
 
    # ── 4. Stats ──────────────────────────────────────────────────────────────
    from app.models.visamodels import Deadline
 
    verified_docs = sum(1 for d in docs if d.status == "verified")
 
    # Next deadline
    deadline_result = await db.execute(
        select(Deadline)
        .where(
            Deadline.user_id    == link.employee_id,
            Deadline.is_completed == False,
            Deadline.is_dismissed == False,
            Deadline.due_date >= datetime.now(timezone.utc),
        )
        .order_by(Deadline.due_date.asc())
        .limit(1)
    )
    next_deadline = deadline_result.scalars().first()
    next_deadline_days = None
    if next_deadline:
        delta = next_deadline.due_date - datetime.now(timezone.utc)
        next_deadline_days = max(0, delta.days)
 
    stats = {
        "active_cases":       len(active_apps),
        "total_cases":        len(all_apps),
        "documents_total":    len(docs),
        "documents_verified": verified_docs,
        "next_deadline_days": next_deadline_days,
    }
 
    # ── 5. Activity (last 10 status changes + doc events) ─────────────────────
    history_result = await db.execute(
        select(ApplicationStatusHistory)
        .where(ApplicationStatusHistory.application_id.in_([a.id for a in all_apps]))
        .order_by(ApplicationStatusHistory.created_at.desc())
        .limit(10)
    )
    history_items = history_result.scalars().all()
 
    activity = []
    dot_map = {
        "approved": "green", "submitted": "blue",
        "action_needed": "orange", "rfe_response": "orange",
        "in_progress": "blue", "draft": "gray",
        "rejected": "gray", "withdrawn": "gray",
    }
    for h in history_items:
        # Resolve actor name
        actor_user = await db_get_by_id(db, User, h.changed_by) if h.changed_by else None
        actor_label = (f"{actor_user.first_name} {actor_user.last_name}".strip()
                       if actor_user else "System")
        activity.append({
            "id":          str(h.id),
            "title":       f"{h.status.replace('_', ' ').title()} — {h.stage.replace('_', ' ').title()}",
            "actor":       f"By {actor_label}",
            "occurred_at": h.created_at.isoformat(),
            "dot_color":   dot_map.get(h.status, "gray"),
        })
 
    # ── 6. Visa info from most recent app ─────────────────────────────────────
    visa_code = None
    if all_apps:
        latest_vt_result = await db.execute(
            select(VisaType).where(VisaType.id == all_apps[0].visa_type_id)
        )
        latest_vt = latest_vt_result.scalars().first()
        if latest_vt:
            visa_code = latest_vt.code
 
    # ── 7. Assemble response ──────────────────────────────────────────────────
    return {
        "profile": {
            "employee_link_id":    str(link.id),
            "user_id":             str(link.employee_id),
            "full_name":           full_name,
            "email":               emp_user.email if emp_user else "",
            "profile_picture_url": emp_profile.profile_picture_url if emp_profile else None,
            "job_title":           link.job_title,
            "department":          link.department,
            "work_email":          link.work_email,
            "start_date":          str(link.start_date) if link.start_date else None,
            "company_name":        employer.company_name if employer else None,
            "company_location":    f"{employer.city}, {employer.state}".strip(", ") if employer and employer.city else None,
            "visa_code":           visa_code,
            "visa_status_label":   "Active" if active_apps else "No Active Visa",
            "linked_at":           link.created_at.isoformat(),
            "is_active":           link.is_active,
        },
        "stats":       stats,
        "active_case": active_case_summary,
        "all_cases":   all_cases_summary,
        "documents":   documents_summary,
        "activity":    activity,
    }