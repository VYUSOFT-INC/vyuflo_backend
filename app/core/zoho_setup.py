# app/core/zoho_setup.py
"""
Reads your SQLAlchemy models and auto-creates matching tables in Zoho Analytics.
"""
import httpx
from sqlalchemy import inspect
from app.core.database import engine
from app.core.zoho_client import zoho_client

# SQLAlchemy → Zoho column type mapping
TYPE_MAP = {
    "INTEGER":   "NUMBER",
    "VARCHAR":   "PLAIN",
    "TEXT":      "PLAIN",
    "BOOLEAN":   "BOOLEAN",
    "DATETIME":  "DATE",
    "FLOAT":     "NUMBER",
    "JSON":      "PLAIN",
}

async def create_zoho_tables_from_models():
    """Inspect all 37 SQLAlchemy tables and create them in Zoho Analytics."""
    token = await zoho_client.get_access_token()
    
    async with engine.connect() as conn:
        inspector = inspect(conn)  # sync inspect on async engine
        table_names = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
    
    print(f"Found {len(table_names)} tables: {table_names}")
    
    results = {}
    async with httpx.AsyncClient() as client:
        for table in table_names:
            columns = await _get_columns(table)
            payload = {
                "viewName": table,
                "columns": columns
            }
            resp = await client.post(
                f"{zoho_client.BASE_URL}/workspaces/{zoho_client.workspace_id}/views",
                headers={"Authorization": f"Zoho-oauthtoken {token}"},
                json=payload
            )
            results[table] = resp.status_code
            print(f"  ✅ {table} → {resp.status_code}")
    
    return results

async def _get_columns(table_name: str) -> list[dict]:
    """Convert SQLAlchemy columns to Zoho Analytics column schema."""
    async with engine.connect() as conn:
        cols = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_columns(table_name)
        )
    
    zoho_cols = []
    for col in cols:
        col_type = type(col["type"]).__name__.upper()
        zoho_cols.append({
            "columnName": col["name"],
            "dataType": TYPE_MAP.get(col_type, "PLAIN"),
            "description": f"Imported from SQLAlchemy model: {table_name}"
        })
    return zoho_cols