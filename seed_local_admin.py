import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.visamodels import User, UserProfile, UserRole, Role, UserEmail

OLD = "admin@vyuflo.local"
NEW = "admin@vyuflo.com"
SUPER = "superadmin@vyuflo.com"
PASSWORD = "password"
ROLE_NAME = "super_admin"


async def _ensure_login_email(db, user: User, email: str) -> None:
    """Login looks up verified user_emails rows — users.email alone is not enough."""
    normalized = email.lower().strip()
    linked = (
        await db.execute(select(UserEmail).where(UserEmail.email == normalized))
    ).scalar_one_or_none()
    if linked is None:
        db.add(UserEmail(
            user_id=user.id,
            email=normalized,
            is_verified=True,
            is_primary=True,
            source="signup",
        ))
        print("CREATED_USER_EMAIL", normalized)
    else:
        linked.user_id = user.id
        linked.is_verified = True
        linked.is_primary = True
        print("USER_EMAIL_OK", normalized)


async def _ensure(db, email: str, first: str, last: str, role) -> None:
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    old = (await db.execute(select(User).where(User.email == OLD))).scalar_one_or_none() if email == NEW else None

    if user is None and old is not None:
        old.email = NEW
        old.password_hash = hash_password(PASSWORD)
        old.is_active = True
        old.is_verified = True
        old.terms_accepted = True
        old.is_platform_user = True
        user = old
        print("RENAMED", OLD, "->", NEW)
    elif user is None:
        user = User(
            first_name=first, last_name=last, email=email,
            password_hash=hash_password(PASSWORD), auth_provider="email",
            is_active=True, is_verified=True, terms_accepted=True,
            is_platform_user=True,
        )
        db.add(user)
        await db.flush()
        print("CREATED", email)
    else:
        user.password_hash = hash_password(PASSWORD)
        user.is_active = True
        user.is_verified = True
        user.terms_accepted = True
        user.is_platform_user = True
        print("UPDATED", email)

    profile = (await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))).scalar_one_or_none()
    if profile is None:
        db.add(UserProfile(user_id=user.id, full_legal_name=f"{first} {last}", onboarding_step=4, onboarding_completed=True))
        print("CREATED_PROFILE", email)
    else:
        profile.onboarding_step = 4
        profile.onboarding_completed = True

    await _ensure_login_email(db, user, email)

    ur = (await db.execute(select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id))).scalar_one_or_none()
    if ur is None:
        others = (await db.execute(select(UserRole).where(UserRole.user_id == user.id))).scalars().all()
        for o in others:
            await db.delete(o)
        db.add(UserRole(user_id=user.id, role_id=role.id))
        print("ASSIGNED_ROLE", email)
    else:
        print("ROLE_OK", email)


async def main():
    async with AsyncSessionLocal() as db:
        role = (await db.execute(select(Role).where(Role.name == ROLE_NAME))).scalar_one_or_none()
        if role is None:
            print("ROLE_MISSING", ROLE_NAME); return

        await _ensure(db, NEW, "Vyuflo", "Admin", role)
        await _ensure(db, SUPER, "Vyuflo", "SuperAdmin", role)
        await db.commit()
        print("DONE", NEW, "and", SUPER)

asyncio.run(main())
