"""add Google/GitHub OAuth support to users

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-09

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # OAuth-only accounts have no password.
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=True)

    op.add_column("users", sa.Column("oauth_provider", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("oauth_provider_id", sa.String(length=255), nullable=True))

    # NULLs don't collide under a standard unique constraint, so password-only
    # accounts (both columns NULL) are unaffected; this only enforces that a
    # given provider account can't be linked to more than one user.
    op.create_unique_constraint(
        "uq_users_oauth_provider_identity", "users", ["oauth_provider", "oauth_provider_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_users_oauth_provider_identity", "users", type_="unique")
    op.drop_column("users", "oauth_provider_id")
    op.drop_column("users", "oauth_provider")
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=False)
