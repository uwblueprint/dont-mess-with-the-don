"""add strikes table

Revision ID: fd23c0ac9d6b
Revises: a1c4e8b90d22
Create Date: 2026-11-18

"""

import sqlalchemy as sa
from alembic import op

revision = "fd23c0ac9d6b"
down_revision = "a1c4e8b90d22"
branch_labels = None
depends_on = None

strikereason = sa.Enum("no_show", "late_cancellation", "manual", name="strikereason")


def upgrade():
    op.create_table(
        "strikes",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("registration_id", sa.Integer(), nullable=True),
        sa.Column("reason", strikereason, nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("issued_by", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_by", sa.Integer(), nullable=True),
        sa.Column("revoke_reason", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.ForeignKeyConstraint(["registration_id"], ["registrations.id"]),
        sa.ForeignKeyConstraint(["issued_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["revoked_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("registration_id", name="strikes_registration_id_key"),
    )
    op.create_index(op.f("ix_strikes_user_id"), "strikes", ["user_id"])


def downgrade():
    op.drop_index(op.f("ix_strikes_user_id"), table_name="strikes")
    op.drop_table("strikes")
    strikereason.drop(op.get_bind())
