# app/services/invitation_service.py
import uuid
import secrets
import string
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.visamodels import (
    EmployerInvitation,
    EmployerEmployee,
    EmployerProfile,
    UserProfile,
    User,
    Application,
)

from app.schemas.hr.invitation_schemas import (
    InviteByEmailRequest,
    InviteByCodeRequest,
    InviteByLinkRequest,
    AcceptInviteRequest,
    UpdateEmployeeRequest,
)
from app.services.services import db_create, db_get_by_id, db_update


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
    Employee enters code on VisaFlow to connect.
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

    return {
        "valid":         True,
        "company_name":  employer.company_name if employer else "Unknown Company",
        "hr_name":       hr_name,
        "invite_method": invite.invite_method,
        "message":       f"Valid invite from {employer.company_name if employer else 'a company'}",
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

    now = datetime.now(timezone.utc)

    # ── Step 1: Create employer_employees record ──────────────────────────────
    link = EmployerEmployee(
        employer_id         = invite.created_by,         # HR user's user.id
        employee_id         = employee_id,
        employer_profile_id = invite.employer_profile_id,
        invitation_id       = invite.id,
        is_active           = True,
        created_by          = employee_id,
    )
    await db_create(db, link)

    # ── Step 2: Update user_profiles.employer_id ──────────────────────────────
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == employee_id)
    )
    profile = profile_result.scalars().first()
    if profile:
        await db_update(db, UserProfile, profile.id, {
            "employer_id": invite.employer_profile_id,
            "invited_by":  invite.created_by,
        })

    # ── Step 3: Update invite status ─────────────────────────────────────────
    if invite.max_uses and invite.max_uses == 1:
        # Single-use invite (email method) — mark fully accepted
        await db_update(db, EmployerInvitation, invite.id, {
            "status":      "accepted",
            "accepted_by": employee_id,
            "accepted_at": now,
            "used_count":  invite.used_count + 1,
        })
    else:
        # Multi-use invite (code/link) — just increment count
        await db_update(db, EmployerInvitation, invite.id, {
            "used_count":  invite.used_count + 1,
            "accepted_by": employee_id,   # last accepted_by
            "accepted_at": now,
        })

    # ── Step 4: Auto-assign HR to existing applications ───────────────────────
    # Any applications this employee has without an HR assigned
    await db.execute(
        Application.__table__.update()
        .where(
            Application.user_id        == employee_id,
            Application.assigned_hr_id == None,
        )
        .values(assigned_hr_id=invite.created_by)
    )

    return {
        "message":      f"Successfully linked to {employer.company_name}",
        "company_name": employer.company_name,
        "employer_id":  invite.employer_profile_id,
    }


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