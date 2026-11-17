"""add unique event-series occurrence constraint

Revision ID: 7c9d2e1f4a6b
Revises: 74faec6fcc21
Create Date: 2026-10-26

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "7c9d2e1f4a6b"
down_revision = "74faec6fcc21"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint(
        "uq_events_event_series_start_datetime",
        "events",
        ["event_series_id", "start_datetime"],
    )


def downgrade():
    op.drop_constraint("uq_events_event_series_start_datetime", "events", type_="unique")
