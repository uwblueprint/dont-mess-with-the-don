"""add check_in_token to events

Revision ID: 71cf4c442595
Revises: 74faec6fcc21
Create Date: 2026-11-13 18:38:24

"""
import secrets

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision = "71cf4c442595"
down_revision = "74faec6fcc21"
branch_labels = None
depends_on = None


def upgrade():
    # Nullable first so existing rows don't violate NOT NULL
    op.add_column(
        "events",
        sa.Column(
            "check_in_token",
            sqlmodel.sql.sqltypes.AutoString(length=64),
            nullable=True,
        ),
    )

    # Backfill each existing event with its own token, matching the format the
    # Event model generates (app.models.event.generate_check_in_token)
    conn = op.get_bind()
    event_ids = conn.execute(sa.text("SELECT id FROM events")).scalars().all()
    for event_id in event_ids:
        conn.execute(
            sa.text("UPDATE events SET check_in_token = :token WHERE id = :id"),
            {"token": secrets.token_urlsafe(32), "id": event_id},
        )

    op.alter_column("events", "check_in_token", nullable=False)
    op.create_unique_constraint("events_check_in_token_key", "events", ["check_in_token"])


def downgrade():
    op.drop_constraint("events_check_in_token_key", "events", type_="unique")
    op.drop_column("events", "check_in_token")
