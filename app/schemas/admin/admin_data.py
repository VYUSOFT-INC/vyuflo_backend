"""Schemas for Admin Data browser (RBAC P2)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AdminDataColumnMeta(BaseModel):
    name: str
    type: str
    nullable: bool = True
    redacted: bool = False
    primary_key: bool = False


class AdminDataTableMeta(BaseModel):
    name: str
    label: str
    pk: List[str]
    row_count: int = 0
    writable: bool = True
    readonly_reason: Optional[str] = None
    columns: List[AdminDataColumnMeta] = Field(default_factory=list)


class AdminDataTablesResponse(BaseModel):
    tables: List[AdminDataTableMeta]


class AdminDataRowsResponse(BaseModel):
    table: str
    page: int
    page_size: int
    total: int
    rows: List[Dict[str, Any]]


class AdminDataRowResponse(BaseModel):
    table: str
    row: Dict[str, Any]


class AdminDataRowWriteRequest(BaseModel):
    """Create/update payload — keys are column names."""
    data: Dict[str, Any] = Field(default_factory=dict)
