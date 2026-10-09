"""add oauth_login_codes table for one-time OAuth session exchange

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-09

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "oauth_login_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_oauth_login_codes_code_hash", "oauth_login_codes", ["code_hash"], unique=True
    )
    op.create_index("ix_oauth_login_codes_expires_at", "oauth_login_codes", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_oauth_login_codes_expires_at", table_name="oauth_login_codes")
    op.drop_index("ix_oauth_login_codes_code_hash", table_name="oauth_login_codes")
    op.drop_table("oauth_login_codes")
