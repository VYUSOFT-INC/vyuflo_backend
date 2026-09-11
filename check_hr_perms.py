import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.visamodels import User
from app.core.core_permissions import get_effective_permissions, get_permission_breakdown

EMAIL = "hr@vyuflo.com"

async def main():
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == EMAIL))).scalar_one()
        print("user_id", user.id)
        bd = await get_permission_breakdown(user.id, db)
        print("deny", bd["deny"])
        print("hr.invite_in_role", "hr.invite" in bd["role"])
        print("hr.invite_in_effective", "hr.invite" in bd["effective"])
        print("effective_has_invite", "hr.invite" in bd["effective"])
        eff = await get_effective_permissions(user.id, db)
        print("eff_has_invite", "hr.invite" in eff)

asyncio.run(main())
