"""hackathons table, seeded with the three existing public workshop/hackathon items

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ECELL_WORKSHOPS = [
    ("Blue Dart Workshop", "Workshop & Hackathon/E-Cell IIT Roorkee/BLUE DART WORKSHOP.pdf"),
    ("HiLabs Workshop", "Workshop & Hackathon/E-Cell IIT Roorkee/HILABS WORKSHOP.pdf"),
    ("Tech Workshop by Microsoft Azure Cloud Specialist", "Workshop & Hackathon/E-Cell IIT Roorkee/Tech Workshop by Microsoft Azure Cloud Specialist.pdf"),
    ("Biz Quiz", "Workshop & Hackathon/E-Cell IIT Roorkee/BIZ QUIZ.pdf"),
    ("Finance Workshop", "Workshop & Hackathon/E-Cell IIT Roorkee/Finance_Workshop_Cred_Product_Specialist.pdf"),
]

hackathons_table = sa.table(
    "hackathons",
    sa.column("title", sa.String),
    sa.column("type", sa.String),
    sa.column("description", sa.Text),
    sa.column("organizer", sa.String),
    sa.column("icon", sa.String),
    sa.column("certificate_url", sa.String),
    sa.column("subitems", sa.JSON(none_as_null=True)),
    sa.column("is_visible", sa.Boolean),
    sa.column("display_order", sa.Integer),
)


def upgrade() -> None:
    op.create_table(
        "hackathons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("organizer", sa.String(length=200), nullable=True),
        sa.Column("date", sa.Date(), nullable=True),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("icon", sa.String(length=40), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("certificate_url", sa.String(length=500), nullable=True),
        sa.Column("event_url", sa.String(length=500), nullable=True),
        sa.Column("subitems", sa.JSON(none_as_null=True), nullable=True),
        sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_hackathons_display_order", "hackathons", ["display_order"])

    # Seed only an empty table, so re-running or editing later never duplicates rows.
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT COUNT(*) FROM hackathons")).scalar() == 0:
        op.bulk_insert(
            hackathons_table,
            [
                {
                    "title": "ET AI Hackathon",
                    "type": "hackathon",
                    "description": "AI hackathon, 2026. Certificate of participation.",
                    "organizer": None,
                    "icon": "bolt",
                    "certificate_url": "Workshop & Hackathon/ET-AI_Hackathon_2026_Certificate_Vansh_Yadav.pdf",
                    "subitems": None,
                    "is_visible": True,
                    "display_order": 0,
                },
                {
                    "title": "E-Cell IIT Roorkee Workshops",
                    "type": "workshop",
                    "description": "A series of workshops by E-Cell IIT Roorkee.",
                    "organizer": "E-Cell IIT Roorkee",
                    "icon": "layers",
                    "certificate_url": None,
                    "subitems": [
                        {"title": title, "certificate_url": url} for title, url in ECELL_WORKSHOPS
                    ],
                    "is_visible": True,
                    "display_order": 1,
                },
                {
                    "title": "ByteXL GenAI Workshop",
                    "type": "workshop",
                    "description": "GenAI workshop by ByteXL.",
                    "organizer": "ByteXL",
                    "icon": "clock",
                    "certificate_url": "Workshop & Hackathon/byteXl workshop.pdf",
                    "subitems": None,
                    "is_visible": True,
                    "display_order": 2,
                },
            ],
        )


def downgrade() -> None:
    op.drop_index("ix_hackathons_display_order", table_name="hackathons")
    op.drop_table("hackathons")
