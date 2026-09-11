"""
Admin Data browser — allowlisted ORM tables, redaction, CRUD + audit.

Security:
- Only tables present on SQLAlchemy Base.metadata
- Secrets redacted on read; never writable
- Dangerous tables forced read-only
- All writes audited
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import Table, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.models.visamodels import AuditLog

# Tables that must never be mutated via the data browser
READONLY_TABLES: dict[str, str] = {
    "password_reset_tokens": "Auth tokens are read-only",
    "user_otp": "OTP codes are read-only",
    "push_subscriptions": "Push endpoints are read-only",
    "audit_logs": "Audit log is append-only via the system",
    "user_login_history": "Login history is system-managed",
}

# Column name patterns that are redacted / non-writable
_REDACT_RE = re.compile(
    r"(password|secret|token|api[_-]?key|private[_-]?key|refresh|salt|hash)",
    re.I,
)

_REDACTED_PLACEHOLDER = "***REDACTED***"


def _label(name: str) -> str:
    return name.replace("_", " ").title()


def _is_redacted_col(name: str) -> bool:
    return bool(_REDACT_RE.search(name))


def _serialize(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (bytes, bytearray)):
        return _REDACTED_PLACEHOLDER
    if isinstance(value, (list, dict, bool, int, float, str)):
        return value
    return str(value)


def _get_table(table_name: str) -> Table:
    if table_name not in Base.metadata.tables:
        raise NotFoundException(f"Table not found: {table_name}")
    return Base.metadata.tables[table_name]


def _pk_cols(table: Table) -> list[str]:
    return [c.name for c in table.primary_key.columns]


def _writable_info(table_name: str) -> tuple[bool, Optional[str]]:
    if table_name in READONLY_TABLES:
        return False, READONLY_TABLES[table_name]
    return True, None


async def _row_count(db: AsyncSession, table: Table) -> int:
    result = await db.execute(select(func.count()).select_from(table))
    return int(result.scalar_one() or 0)


def _column_meta(table: Table) -> list[dict]:
    pk = set(_pk_cols(table))
    cols = []
    for col in table.columns:
        cols.append(
            {
                "name": col.name,
                "type": type(col.type).__name__,
                "nullable": bool(col.nullable),
                "redacted": _is_redacted_col(col.name),
                "primary_key": col.name in pk,
            }
        )
    return cols


def _redact_row(row: dict) -> dict:
    out = {}
    for k, v in row.items():
        if _is_redacted_col(k):
            out[k] = _REDACTED_PLACEHOLDER if v is not None else None
        else:
            out[k] = _serialize(v)
    return out


async def list_tables(db: AsyncSession) -> list[dict]:
    tables: list[dict] = []
    for name in sorted(Base.metadata.tables.keys()):
        table = Base.metadata.tables[name]
        writable, reason = _writable_info(name)
        try:
            count = await _row_count(db, table)
        except Exception:
            count = 0
        tables.append(
            {
                "name": name,
                "label": _label(name),
                "pk": _pk_cols(table),
                "row_count": count,
                "writable": writable,
                "readonly_reason": reason,
                "columns": _column_meta(table),
            }
        )
    return tables


async def list_rows(
    db: AsyncSession,
    table_name: str,
    page: int = 1,
    page_size: int = 50,
    q: Optional[str] = None,
) -> dict:
    table = _get_table(table_name)
    page = max(1, page)
    page_size = min(max(1, page_size), 200)
    offset = (page - 1) * page_size

    stmt = select(table)
    if q:
        # OR across string-like columns (non-redacted)
        from sqlalchemy import String, or_

        clauses = []
        for col in table.columns:
            if _is_redacted_col(col.name):
                continue
            try:
                clauses.append(col.cast(String).ilike(f"%{q}%"))
            except Exception:
                continue
        if clauses:
            stmt = stmt.where(or_(*clauses))

    total = await _row_count(db, table) if not q else None
    if q:
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await db.execute(count_stmt)).scalar_one() or 0)

    # stable order by PK when possible
    pk = _pk_cols(table)
    if pk:
        stmt = stmt.order_by(*[table.c[c] for c in pk])
    stmt = stmt.offset(offset).limit(page_size)
    result = await db.execute(stmt)
    rows = [_redact_row(dict(r._mapping)) for r in result]

    return {
        "table": table_name,
        "page": page,
        "page_size": page_size,
        "total": int(total or 0),
        "rows": rows,
    }


def _pk_filter(table: Table, row_id: str):
    pk = _pk_cols(table)
    if len(pk) != 1:
        raise BadRequestException("Composite primary keys are not supported for row ops yet.")
    col = table.c[pk[0]]
    # try uuid then raw
    try:
        return col == uuid.UUID(row_id)
    except ValueError:
        return col == row_id


async def get_row(db: AsyncSession, table_name: str, row_id: str) -> dict:
    table = _get_table(table_name)
    result = await db.execute(select(table).where(_pk_filter(table, row_id)))
    row = result.mappings().first()
    if not row:
        raise NotFoundException("Row not found.")
    return {"table": table_name, "row": _redact_row(dict(row))}


def _sanitize_write(table: Table, data: dict, *, is_update: bool) -> dict:
    allowed = {c.name for c in table.columns}
    cleaned: dict[str, Any] = {}
    for k, v in data.items():
        if k not in allowed:
            raise BadRequestException(f"Unknown column: {k}")
        if _is_redacted_col(k):
            raise BadRequestException(f"Column is not writable: {k}")
        if is_update and k in _pk_cols(table):
            raise BadRequestException("Primary key cannot be updated.")
        # coerce UUID strings
        col = table.c[k]
        if v is not None and "UUID" in type(col.type).__name__:
            try:
                v = uuid.UUID(str(v))
            except ValueError as e:
                raise BadRequestException(f"Invalid UUID for {k}") from e
        cleaned[k] = v
    return cleaned


async def _audit(
    db: AsyncSession,
    *,
    actor_id: uuid.UUID,
    action: str,
    table_name: str,
    resource_id: Optional[uuid.UUID],
    old_value: Any,
    new_value: Any,
):
    db.add(
        AuditLog(
            actor_id=actor_id,
            actor_type="user",
            action=action,
            resource_type=f"admin_data:{table_name}",
            resource_id=resource_id if isinstance(resource_id, uuid.UUID) else None,
            old_value=json.dumps(old_value, default=str) if old_value is not None else None,
            new_value=json.dumps(new_value, default=str) if new_value is not None else None,
            description=f"Admin data browser {action} on {table_name}",
            severity="warning",
        )
    )


async def create_row(
    db: AsyncSession, table_name: str, data: dict, actor_id: uuid.UUID
) -> dict:
    writable, reason = _writable_info(table_name)
    if not writable:
        raise ForbiddenException(reason or "Table is read-only.")
    table = _get_table(table_name)
    cleaned = _sanitize_write(table, data, is_update=False)
    if not cleaned:
        raise BadRequestException("No writable fields provided.")
    stmt = table.insert().values(**cleaned).returning(*table.columns)
    result = await db.execute(stmt)
    row = dict(result.mappings().one())
    pk = _pk_cols(table)
    rid = row.get(pk[0]) if len(pk) == 1 else None
    await _audit(
        db,
        actor_id=actor_id,
        action="admin_data.create",
        table_name=table_name,
        resource_id=rid if isinstance(rid, uuid.UUID) else None,
        old_value=None,
        new_value=_redact_row(row),
    )
    await db.commit()
    return {"table": table_name, "row": _redact_row(row)}


async def update_row(
    db: AsyncSession, table_name: str, row_id: str, data: dict, actor_id: uuid.UUID
) -> dict:
    writable, reason = _writable_info(table_name)
    if not writable:
        raise ForbiddenException(reason or "Table is read-only.")
    table = _get_table(table_name)
    existing = await db.execute(select(table).where(_pk_filter(table, row_id)))
    old = existing.mappings().first()
    if not old:
        raise NotFoundException("Row not found.")
    cleaned = _sanitize_write(table, data, is_update=True)
    if not cleaned:
        raise BadRequestException("No writable fields provided.")
    stmt = (
        table.update()
        .where(_pk_filter(table, row_id))
        .values(**cleaned)
        .returning(*table.columns)
    )
    result = await db.execute(stmt)
    row = dict(result.mappings().one())
    pk = _pk_cols(table)
    rid = row.get(pk[0]) if len(pk) == 1 else None
    await _audit(
        db,
        actor_id=actor_id,
        action="admin_data.update",
        table_name=table_name,
        resource_id=rid if isinstance(rid, uuid.UUID) else None,
        old_value=_redact_row(dict(old)),
        new_value=_redact_row(row),
    )
    await db.commit()
    return {"table": table_name, "row": _redact_row(row)}


async def delete_row(
    db: AsyncSession, table_name: str, row_id: str, actor_id: uuid.UUID
) -> None:
    writable, reason = _writable_info(table_name)
    if not writable:
        raise ForbiddenException(reason or "Table is read-only.")
    table = _get_table(table_name)
    existing = await db.execute(select(table).where(_pk_filter(table, row_id)))
    old = existing.mappings().first()
    if not old:
        raise NotFoundException("Row not found.")
    await db.execute(table.delete().where(_pk_filter(table, row_id)))
    pk = _pk_cols(table)
    rid = dict(old).get(pk[0]) if len(pk) == 1 else None
    await _audit(
        db,
        actor_id=actor_id,
        action="admin_data.delete",
        table_name=table_name,
        resource_id=rid if isinstance(rid, uuid.UUID) else None,
        old_value=_redact_row(dict(old)),
        new_value=None,
    )
    await db.commit()
