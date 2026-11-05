"""add notification_body to events and event_types

Revision ID: a1c4e8b90d22
Revises: 2eceb5b619b4
Create Date: 2026-10-07

"""

import sqlalchemy as sa
from alembic import op

revision = "a1c4e8b90d22"
down_revision = "2eceb5b619b4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("event_types", sa.Column("notification_body", sa.Text(), nullable=True))
    op.add_column("events", sa.Column("notification_body", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("events", "notification_body")
    op.drop_column("event_types", "notification_body")
