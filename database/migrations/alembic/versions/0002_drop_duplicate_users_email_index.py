"""drop duplicate users.email index

The unique constraint created by 0001 (unique=True on the column) already
enforces uniqueness, so the separate ix_users_email unique index was redundant.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-04

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")


def downgrade() -> None:
    op.create_index("ix_users_email", "users", ["email"], unique=True)
