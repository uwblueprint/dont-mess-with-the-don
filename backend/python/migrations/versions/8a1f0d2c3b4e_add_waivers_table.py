"""add waivers table

Revision ID: 8a1f0d2c3b4e
Revises: b945a06e4bdd
Create Date: 2026-06-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision = "8a1f0d2c3b4e"
down_revision = "b945a06e4bdd"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "waivers",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("event_type", sa.Uuid(), nullable=True),
        sa.Column("document_url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["event_type"], ["event_types.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("waivers")
