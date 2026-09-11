import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.visamodels import User, UserEmail
from app.services.employee.auth_services import service_login

EMAIL = "admin@vyuflo.com"

async def main():
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == EMAIL))).scalar_one()
        row = (await db.execute(select(UserEmail).where(UserEmail.email == EMAIL))).scalar_one_or_none()
        if row is None:
            db.add(UserEmail(user_id=user.id, email=EMAIL, is_verified=True, is_primary=True, source="signup"))
            await db.commit()
            print("ADDED_USER_EMAIL")
        else:
            row.is_verified = True
            row.is_primary = True
            row.user_id = user.id
            await db.commit()
            print("UPDATED_USER_EMAIL")

    async with AsyncSessionLocal() as db:
        result = await service_login(db, email=EMAIL, password="password")
        print("LOGIN_OK", result["roles"], result["user"]["email"])

asyncio.run(main())
