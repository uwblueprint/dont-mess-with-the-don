"""add waiver_signed table for completed waivers

Revision ID: c4e8b2a19d37
Revises: a7c3e91d5f20
Create Date: 2026-11-16 00:00:00.000000

Signed waivers are legal records, so every foreign key is RESTRICT: a user, event or
template that a signed waiver points at cannot be deleted.
"""
from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision = "c4e8b2a19d37"
down_revision = "a7c3e91d5f20"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "waiver_signed",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("signed_by_user_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("waiver_template_id", sa.Uuid(), nullable=False),
        sa.Column("document_key", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("signed_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["signed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["waiver_template_id"], ["waiver_template.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "event_id",
            "waiver_template_id",
            name="uq_waiver_signed_user_event_template",
        ),
    )
    op.create_index(op.f("ix_waiver_signed_user_id"), "waiver_signed", ["user_id"])
    op.create_index(op.f("ix_waiver_signed_event_id"), "waiver_signed", ["event_id"])


def downgrade():
    op.drop_index(op.f("ix_waiver_signed_event_id"), table_name="waiver_signed")
    op.drop_index(op.f("ix_waiver_signed_user_id"), table_name="waiver_signed")
    op.drop_table("waiver_signed")
