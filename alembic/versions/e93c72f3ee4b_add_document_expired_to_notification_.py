"""add document_expired to notification_type_enum

Revision ID: e93c72f3ee4b
Revises: 0cf0af3ce2d2
Create Date: 2026-09-01 19:09:41.213756

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e93c72f3ee4b'
down_revision: Union[str, None] = '0cf0af3ce2d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE notification_type_enum ADD VALUE IF NOT EXISTS 'document_expired'")


def downgrade() -> None:
    # Postgres has no DROP VALUE for enums — same limitation as the
    # document_status_enum migration. No-op.
    pass
