"""add display_order to projects and certificates

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "certificates",
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
    )

    bind = op.get_bind()
    # Backfill using the order these rows were previously returned in (created_at desc,
    # id desc, matching the old query), so existing content does not visually reshuffle.
    bind.execute(
        sa.text(
            """
            UPDATE projects AS p
            SET display_order = ranked.rn - 1
            FROM (
                SELECT id, ROW_NUMBER() OVER (ORDER BY created_at DESC, id DESC) AS rn
                FROM projects
            ) AS ranked
            WHERE p.id = ranked.id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE certificates AS c
            SET display_order = ranked.rn - 1
            FROM (
                SELECT id, ROW_NUMBER() OVER (ORDER BY created_at DESC, id DESC) AS rn
                FROM certificates
            ) AS ranked
            WHERE c.id = ranked.id
            """
        )
    )

    op.create_index("ix_projects_display_order", "projects", ["display_order"])
    op.create_index("ix_certificates_display_order", "certificates", ["display_order"])


def downgrade() -> None:
    op.drop_index("ix_certificates_display_order", table_name="certificates")
    op.drop_index("ix_projects_display_order", table_name="projects")
    op.drop_column("certificates", "display_order")
    op.drop_column("projects", "display_order")
