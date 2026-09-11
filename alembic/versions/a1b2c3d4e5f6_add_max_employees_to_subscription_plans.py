"""add max_employees to subscription_plans

Revision ID: a1b2c3d4e5f6
Revises: e93c72f3ee4b
Create Date: 2026-09-11 08:55:00.000000

Idempotent add of subscription_plans.max_employees (nullable int, null=unlimited),
mirroring max_applications / max_documents / max_messages.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import ProgrammingError


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "e93c72f3ee4b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _safe(label: str, fn) -> None:
    """SAVEPOINT-tolerant op wrapper (see 7106bbc1c756)."""
    bind = op.get_bind()
    savepoint = bind.begin_nested()
    try:
        fn()
    except ProgrammingError as e:
        savepoint.rollback()
        msg = str(getattr(e, "orig", None) or e).lower()
        if "already exists" in msg or "does not exist" in msg:
            print(f"Skipping '{label}' — already in desired state")
        else:
            raise
    else:
        savepoint.commit()


def upgrade() -> None:
    _safe(
        "subscription_plans.max_employees",
        lambda: op.add_column(
            "subscription_plans",
            sa.Column("max_employees", sa.Integer(), nullable=True),
        ),
    )


def downgrade() -> None:
    _safe(
        "drop subscription_plans.max_employees",
        lambda: op.drop_column("subscription_plans", "max_employees"),
    )
