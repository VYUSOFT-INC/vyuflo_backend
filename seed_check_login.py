import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password, verify_password
from app.models.visamodels import User
from app.services.employee.auth_services import service_login

async def main():
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == "admin@vyuflo.com"))).scalar_one_or_none()
        print("user", bool(user), "active", getattr(user, "is_active", None), "hash_prefix", (user.password_hash or "")[:20] if user else None)
        if user:
            print("verify", verify_password("password", user.password_hash))
        try:
            result = await service_login(db, email="admin@vyuflo.com", password="password")
            print("service_login_ok", result.get("roles"), result.get("user", {}).get("email"))
        except Exception as e:
            print("service_login_err", type(e).__name__, str(e))

asyncio.run(main())
