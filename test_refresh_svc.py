import asyncio, json
from app.core.database import AsyncSessionLocal
from app.core.security import create_refresh_token, new_session_id
from app.services.employee.auth_services import service_refresh_token, _store_refresh_token
from app.services.employee.services import get_user_role
import uuid

UID = "1898a920-a4fb-47a8-a3ac-901a4475adf4"

async def main():
    async with AsyncSessionLocal() as db:
        sid = new_session_id()
        rt = create_refresh_token(UID, sid)
        await _store_refresh_token(UID, sid, rt)
        result = await service_refresh_token(db, refresh_token=rt)
        print("roles", result.get("roles"))
        print("user", result.get("user"))
        print("keys", sorted(result.keys()))

asyncio.run(main())
