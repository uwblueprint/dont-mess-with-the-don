"""merge attendance rename and event_series heads

Revision ID: 2eceb5b619b4
Revises: b44f8a7eab3c, c3a1d8e9f012
Create Date: 2026-09-22

Merge-only revision. #20 (attendance rename) and #27 (event_series) both branched
from 0746657dd317 and merged independently, leaving two heads, which makes
`alembic upgrade head` fail. The two touch disjoint tables (attendance vs.
events/event_series), so no reconciling DDL is needed here.

"""

# revision identifiers, used by Alembic.
revision = "2eceb5b619b4"
down_revision = ("b44f8a7eab3c", "c3a1d8e9f012")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
