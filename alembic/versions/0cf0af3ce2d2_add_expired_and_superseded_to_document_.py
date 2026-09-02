"""add expired and superseded to document_status_enum

Revision ID: 0cf0af3ce2d2
Revises: 7106bbc1c756
Create Date: 2026-09-01 14:22:27.874075

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0cf0af3ce2d2'
down_revision: Union[str, None] = '7106bbc1c756'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block in
    # Postgres — autocommit_block() takes this statement out of Alembic's
    # normal transaction wrapping so it runs on its own.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE document_status_enum ADD VALUE IF NOT EXISTS 'expired'")
        op.execute("ALTER TYPE document_status_enum ADD VALUE IF NOT EXISTS 'superseded'")

def upgrade() -> None:
    op.execute("ALTER TABLE application_tasks ADD COLUMN IF NOT EXISTS is_renewal BOOLEAN DEFAULT 'false' NOT NULL")
    
def downgrade() -> None:
    # Postgres has no DROP VALUE for enums — removing a value requires
    # rebuilding the type (create new type, migrate the column, drop old
    # type) and would fail outright if any row already uses 'expired' or
    # 'superseded'. Left as a no-op; a real rollback would need a
    # hand-written data migration, not a simple reverse of upgrade().
    pass
