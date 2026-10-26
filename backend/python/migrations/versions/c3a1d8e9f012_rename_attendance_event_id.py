"""rename attendance event_id to event_instance_id

Revision ID: c3a1d8e9f012
Revises: 0746657dd317
Create Date: 2026-07-02

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "c3a1d8e9f012"
down_revision = "0746657dd317"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(
        "attendance_user_id_event_id_key",
        "attendance",
        type_="unique",
    )
    op.drop_constraint(
        "attendance_event_id_fkey",
        "attendance",
        type_="foreignkey",
    )
    op.alter_column(
        "attendance",
        "event_id",
        new_column_name="event_instance_id",
    )
    op.create_foreign_key(
        "attendance_event_instance_id_fkey",
        "attendance",
        "events",
        ["event_instance_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "attendance_user_id_event_instance_id_key",
        "attendance",
        ["user_id", "event_instance_id"],
    )


def downgrade():
    op.drop_constraint(
        "attendance_user_id_event_instance_id_key",
        "attendance",
        type_="unique",
    )
    op.drop_constraint(
        "attendance_event_instance_id_fkey",
        "attendance",
        type_="foreignkey",
    )
    op.alter_column(
        "attendance",
        "event_instance_id",
        new_column_name="event_id",
    )
    op.create_foreign_key(
        "attendance_event_id_fkey",
        "attendance",
        "events",
        ["event_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "attendance_user_id_event_id_key",
        "attendance",
        ["user_id", "event_id"],
    )