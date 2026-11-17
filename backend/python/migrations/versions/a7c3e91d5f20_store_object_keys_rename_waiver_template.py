"""store R2 object keys instead of URLs; rename waivers to waiver_template

Revision ID: a7c3e91d5f20
Revises: 7c9d2e1f4a6b
Create Date: 2026-11-16 00:00:00.000000

Renames the image/document URL columns to object-key columns, drops
event_series.image_urls (post-event photos belong to events only) and renames
waivers to waiver_template. Templates no longer point at an event type; instead
events, event types and event series get a waiver_template_id. Written for an
empty database: existing values are not converted, and downgrade does not
restore dropped data.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a7c3e91d5f20"
down_revision = "7c9d2e1f4a6b"
branch_labels = None
depends_on = None

# Tables that point at the waiver template they use
WAIVER_TEMPLATE_TABLES = ["events", "event_types", "event_series"]

# (table, old column, new column)
RENAMES = [
    ("events", "image", "headline_image_key"),
    ("events", "image_urls", "post_event_photo_keys"),
    ("event_series", "image", "headline_image_key"),
    ("event_types", "image", "headline_image_key"),
    ("users", "profile_pic_url", "profile_pic_key"),
    ("waivers", "document_url", "document_key"),
]


def upgrade():
    for table, old, new in RENAMES:
        op.alter_column(table, old, new_column_name=new)
    op.drop_column("event_series", "image_urls")

    op.rename_table("waivers", "waiver_template")
    op.execute("ALTER TABLE waiver_template RENAME CONSTRAINT waivers_pkey TO waiver_template_pkey")
    op.drop_column("waiver_template", "event_type")

    for table in WAIVER_TEMPLATE_TABLES:
        op.add_column(table, sa.Column("waiver_template_id", sa.Uuid(), nullable=True))
        op.create_foreign_key(
            f"{table}_waiver_template_id_fkey",
            table,
            "waiver_template",
            ["waiver_template_id"],
            ["id"],
        )


def downgrade():
    for table in WAIVER_TEMPLATE_TABLES:
        op.drop_constraint(f"{table}_waiver_template_id_fkey", table, type_="foreignkey")
        op.drop_column(table, "waiver_template_id")

    op.add_column("waiver_template", sa.Column("event_type", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "waivers_event_type_fkey", "waiver_template", "event_types", ["event_type"], ["id"]
    )
    op.execute("ALTER TABLE waiver_template RENAME CONSTRAINT waiver_template_pkey TO waivers_pkey")
    op.rename_table("waiver_template", "waivers")
    op.add_column("event_series", sa.Column("image_urls", sa.ARRAY(sa.String()), nullable=True))
    for table, old, new in reversed(RENAMES):
        op.alter_column(table, new, new_column_name=old)
