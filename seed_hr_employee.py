import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.visamodels import User, UserProfile, UserRole, Role, UserEmail

USERS = [
    ("hr@vyuflo.com", "HR", "User", "hr"),
    ("employee@vyuflo.com", "Employee", "User", "employee"),
]
PASSWORD = "password"

async def upsert(db, email, first, last, role_name):
    role = (await db.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
    if role is None:
        print("ROLE_MISSING", role_name)
        return
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None:
        user = User(
            first_name=first, last_name=last, email=email,
            password_hash=hash_password(PASSWORD), auth_provider="email",
            is_active=True, is_verified=True, terms_accepted=True,
        )
        db.add(user)
        await db.flush()
        print("CREATED", email, role_name)
    else:
        user.password_hash = hash_password(PASSWORD)
        user.is_active = True
        user.is_verified = True
        user.terms_accepted = True
        print("UPDATED", email, role_name)

    profile = (await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))).scalar_one_or_none()
    if profile is None:
        db.add(UserProfile(user_id=user.id, full_legal_name=f"{first} {last}", onboarding_step=4, onboarding_completed=True))
    else:
        profile.onboarding_step = 4
        profile.onboarding_completed = True

    ue = (await db.execute(select(UserEmail).where(UserEmail.email == email))).scalar_one_or_none()
    if ue is None:
        db.add(UserEmail(user_id=user.id, email=email, is_verified=True, is_primary=True, source="signup"))
    else:
        ue.user_id = user.id
        ue.is_verified = True
        ue.is_primary = True

    # replace roles with the intended one
    others = (await db.execute(select(UserRole).where(UserRole.user_id == user.id))).scalars().all()
    for o in others:
        await db.delete(o)
    db.add(UserRole(user_id=user.id, role_id=role.id))
    await db.commit()
    print("DONE", email, role_name)

async def main():
    async with AsyncSessionLocal() as db:
        for email, first, last, role in USERS:
            await upsert(db, email, first, last, role)

asyncio.run(main())
