"""add unique event-series occurrence constraint

Revision ID: 7c9d2e1f4a6b
Revises: 28898d337e58
Create Date: 2026-10-26

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "7c9d2e1f4a6b"
down_revision = "28898d337e58"
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
