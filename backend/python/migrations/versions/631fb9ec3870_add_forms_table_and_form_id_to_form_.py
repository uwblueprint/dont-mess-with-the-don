"""add forms table and form_id to form_submissions

Revision ID: 631fb9ec3870
Revises: 8a1f0d2c3b4e
Create Date: 2026-10-19 23:57:57.561015

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "631fb9ec3870"
down_revision = "8a1f0d2c3b4e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "forms",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("form_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column("form_submissions", sa.Column("form_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "form_submissions_form_id_fkey", "form_submissions", "forms", ["form_id"], ["id"]
    )


def downgrade():
    op.drop_constraint("form_submissions_form_id_fkey", "form_submissions", type_="foreignkey")
    op.drop_column("form_submissions", "form_id")
    op.drop_table("forms")
