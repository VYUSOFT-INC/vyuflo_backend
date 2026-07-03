# app/core/zoho_client.py
import httpx
import asyncio
from config import settings

class ZohoClient:
    BASE_URL = "https://analyticsapi.zoho.com/restapi/v2"
    
    def __init__(self):
        self.org_id = settings.ZOHO_ORG_ID
        self.workspace_id = settings.ZOHO_WORKSPACE_ID
        self._access_token = None

    async def get_access_token(self) -> str:
        """Refresh OAuth2 token using client credentials."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://accounts.zoho.com/oauth/v2/token",
                params={
                    "grant_type": "refresh_token",
                    "client_id": settings.ZOHO_CLIENT_ID,
                    "client_secret": settings.ZOHO_CLIENT_SECRET,
                    "refresh_token": settings.ZOHO_REFRESH_TOKEN,
                }
            )
            data = resp.json()
            self._access_token = data["access_token"]
            return self._access_token

    async def import_data(self, table_name: str, rows: list[dict]) -> dict:
        """Push rows into a Zoho Analytics table."""
        token = await self.get_access_token()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.BASE_URL}/workspaces/{self.workspace_id}/views/{table_name}/rows",
                headers={"Authorization": f"Zoho-oauthtoken {token}"},
                json={"rows": rows}
            )
            return resp.json()

zoho_client = ZohoClient()