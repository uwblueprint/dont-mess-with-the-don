"""add role and firebase_uid to users, drop password_hash

Revision ID: 74faec6fcc21
Revises: 631fb9ec3870
Create Date: 2026-11-04 16:50:48

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision = "74faec6fcc21"
down_revision = "631fb9ec3870"
branch_labels = None
depends_on = None

userrole = sa.Enum("attendee", "admin", name="userrole")


def upgrade():
    userrole.create(op.get_bind())
    # Existing users become attendees
    op.add_column(
        "users", sa.Column("role", userrole, nullable=False, server_default="attendee")
    )
    # provider_id was never used; Firebase's uid takes its place
    op.alter_column("users", "provider_id", new_column_name="firebase_uid")
    op.create_unique_constraint("users_firebase_uid_key", "users", ["firebase_uid"])
    # Firebase stores passwords
    op.drop_column("users", "password_hash")


def downgrade():
    op.add_column(
        "users",
        sa.Column("password_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.drop_constraint("users_firebase_uid_key", "users", type_="unique")
    op.alter_column("users", "firebase_uid", new_column_name="provider_id")
    op.drop_column("users", "role")
    userrole.drop(op.get_bind())
