# app/routes/invitation_routes.py
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.visamodels import User
from app.schemas.hr.invitation_schemas import (
    InviteByEmailRequest,
    InviteByCodeRequest,
    InviteByLinkRequest,
    AcceptInviteRequest,
    ValidateTokenRequest,
    UpdateEmployeeRequest,
    InvitationResponse,
    InvitationListResponse,
    AcceptInviteResponse,
    EmployeeListResponse,
    ValidateTokenResponse,
)
from app.services.hr.invitation_service import (
    create_email_invite,
    create_code_invite,
    create_link_invite,
    get_my_invitations,
    revoke_invitation,
    resend_email_invite,
    validate_invite,
    accept_invite,
    get_my_employees,
    update_employee_info,
    deactivate_employee,
)

invitation_router = APIRouter(prefix="/invitations", tags=["Invitations"])


# =============================================================================
# HR — CREATE INVITATIONS
# =============================================================================

@invitation_router.post(
    "/email",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="HR: Invite employee by email",
)
async def invite_by_email(
    data:         InviteByEmailRequest,
    db:           AsyncSession   = Depends(get_db),
    current_user: User           = Depends(get_current_user),
):
    """
    HR sends a targeted email invitation to a specific employee.
    System will send an email with a unique join link.
    The invite expires in `expires_days` days (default 7).
    """
    try:
        invite = await create_email_invite(db, current_user.id, data)
        await db.commit()

        # TODO: send actual email here
        # await send_invitation_email(
        #     to_email=data.email,
        #     invite_token=invite.invite_token,
        #     company_name=...,
        #     hr_name=...,
        #     personal_message=data.personal_message,
        # )

        return invite
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@invitation_router.post(
    "/code",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="HR: Generate reusable company code",
)
async def invite_by_code(
    data:         InviteByCodeRequest,
    db:           AsyncSession   = Depends(get_db),
    current_user: User           = Depends(get_current_user),
):
    """
    HR generates a short reusable code (e.g. VF-TECH-K2X9).
    HR shares this code offline with employees.
    Employee enters the code on VisaFlow to connect to the company.
    """
    try:
        invite = await create_code_invite(db, current_user.id, data)
        await db.commit()
        return invite
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@invitation_router.post(
    "/link",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="HR: Generate shareable invite link",
)
async def invite_by_link(
    data:         InviteByLinkRequest,
    db:           AsyncSession   = Depends(get_db),
    current_user: User           = Depends(get_current_user),
):
    """
    HR generates a shareable link.
    Anyone with the link can join (up to max_uses limit).
    """
    try:
        invite = await create_link_invite(db, current_user.id, data)
        await db.commit()
        return invite
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# HR — MANAGE INVITATIONS
# =============================================================================

@invitation_router.get(
    "/",
    response_model=InvitationListResponse,
    summary="HR: List all sent invitations",
)
async def list_invitations(
    status_filter: Optional[str] = Query(None, alias="status",
                                         description="pending|accepted|expired|revoked"),
    limit:         int           = Query(50, ge=1, le=100),
    offset:        int           = Query(0,  ge=0),
    db:            AsyncSession  = Depends(get_db),
    current_user:  User          = Depends(get_current_user),
):
    """HR lists all invitations they have sent, with optional status filter."""
    items, total = await get_my_invitations(
        db, current_user.id, status_filter, limit, offset
    )
    return {"items": items, "total": total}


@invitation_router.delete(
    "/{invitation_id}",
    status_code=status.HTTP_200_OK,
    summary="HR: Revoke an invitation",
)
async def revoke_invite(
    invitation_id: uuid.UUID,
    db:            AsyncSession = Depends(get_db),
    current_user:  User         = Depends(get_current_user),
):
    """HR revokes a pending invitation. The link/code will no longer work."""
    try:
        await revoke_invitation(db, current_user.id, invitation_id)
        await db.commit()
        return {"message": "Invitation revoked successfully."}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@invitation_router.post(
    "/{invitation_id}/resend",
    response_model=InvitationResponse,
    summary="HR: Resend email invitation with fresh token",
)
async def resend_invite(
    invitation_id: uuid.UUID,
    db:            AsyncSession = Depends(get_db),
    current_user:  User         = Depends(get_current_user),
):
    """HR resends an email invite — generates a new token and resets expiry to 7 days."""
    try:
        invite = await resend_email_invite(db, current_user.id, invitation_id)
        await db.commit()

        # TODO: resend email
        return invite
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# EMPLOYEE — VALIDATE & ACCEPT (PUBLIC — no auth required for validate)
# =============================================================================

@invitation_router.get(
    "/validate",
    response_model=ValidateTokenResponse,
    summary="Public: Validate invite token or code",
)
async def validate_invitation(
    invite_token: Optional[str] = Query(None, description="Token from email/link invite"),
    invite_code:  Optional[str] = Query(None, description="Short code from HR"),
    db:           AsyncSession  = Depends(get_db),
):
    """
    PUBLIC endpoint — no auth required.
    Employee checks if a token/code is valid before signing up.
    Returns company name and HR name so employee can confirm.

    Called when:
    - Employee opens invite link (token in URL)
    - Employee types a company code on signup page
    """
    if not invite_token and not invite_code:
        raise HTTPException(
            status_code=400,
            detail="Provide either invite_token or invite_code."
        )
    result = await validate_invite(db, invite_token, invite_code)
    return result


@invitation_router.post(
    "/accept",
    response_model=AcceptInviteResponse,
    summary="Employee: Accept invitation and link to employer",
)
async def accept_invitation(
    data:         AcceptInviteRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    Employee accepts an invitation.
    This creates the employer_employees record and sets
    user_profiles.employer_id — linking Sai to TechCorp.

    Can be called:
    1. During signup (token/code from URL or form)
    2. After signup from Profile → Connect to Employer
    """
    if not data.invite_token and not data.invite_code:
        raise HTTPException(
            status_code=400,
            detail="Provide either invite_token or invite_code."
        )
    try:
        result = await accept_invite(db, current_user.id, data)
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# HR — MANAGE EMPLOYEES
# =============================================================================

@invitation_router.get(
    "/employees",
    response_model=EmployeeListResponse,
    summary="HR: List all linked employees",
)
async def list_employees(
    is_active:    Optional[bool] = Query(True),
    limit:        int            = Query(50, ge=1, le=100),
    offset:       int            = Query(0,  ge=0),
    db:           AsyncSession   = Depends(get_db),
    current_user: User           = Depends(get_current_user),
):
    """
    HR lists all employees linked to their company.
    Includes active application count per employee.
    """
    items, total = await get_my_employees(
        db, current_user.id, is_active, limit, offset
    )
    return {"items": items, "total": total}


@invitation_router.patch(
    "/employees/{employee_link_id}",
    summary="HR: Update employee job info",
)
async def update_employee(
    employee_link_id: uuid.UUID,
    data:             UpdateEmployeeRequest,
    db:               AsyncSession = Depends(get_db),
    current_user:     User         = Depends(get_current_user),
):
    """HR updates job title, department, work email etc. for a linked employee."""
    try:
        link = await update_employee_info(db, current_user.id, employee_link_id, data)
        await db.commit()
        return {"message": "Employee updated.", "id": str(link.id)}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@invitation_router.delete(
    "/employees/{employee_link_id}",
    summary="HR: Remove employee from company",
)
async def remove_employee(
    employee_link_id: uuid.UUID,
    db:               AsyncSession = Depends(get_db),
    current_user:     User         = Depends(get_current_user),
):
    """
    HR deactivates an employee (soft delete).
    The employee account remains — they just lose the company link.
    """
    try:
        await deactivate_employee(db, current_user.id, employee_link_id)
        await db.commit()
        return {"message": "Employee removed from company."}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))