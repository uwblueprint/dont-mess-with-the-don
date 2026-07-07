"""add unique user event constraint to form_submissions

Revision ID: 3fdb1462e5f7
Revises: 0746657dd317
Create Date: 2026-07-07 01:36:30.775858

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3fdb1462e5f7'
down_revision = '0746657dd317'
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint(
        "uq_form_submissions_user_event",
        "form_submissions",
        ["user_id", "event_instance_id"],
    )


def downgrade():
    op.drop_constraint(
        "uq_form_submissions_user_event",
        "form_submissions",
        type_="unique",
    )
