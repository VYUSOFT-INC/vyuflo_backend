"""add missing expired and superseded values to document_status_enum

Revision ID: d74510a0e8cb
Revises: e93c72f3ee4b
Create Date: 2026-09-07 14:04:37.894481

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd74510a0e8cb'
down_revision: Union[str, None] = 'e93c72f3ee4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block in
    # Postgres — autocommit_block() takes this statement out of Alembic's
    # normal transaction wrapping so it runs on its own.
    # This is a fix for 0cf0af3ce2d2, whose intended upgrade() (adding
    # these enum values) was silently overwritten by a second upgrade()
    # definition later in that same file.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE document_status_enum ADD VALUE IF NOT EXISTS 'expired'")
        op.execute("ALTER TYPE document_status_enum ADD VALUE IF NOT EXISTS 'superseded'")


def downgrade() -> None:
    # Postgres has no DROP VALUE for enums — removing a value requires
    # rebuilding the type and would fail if any row already uses
    # 'expired' or 'superseded'. Left as a no-op.
    pass