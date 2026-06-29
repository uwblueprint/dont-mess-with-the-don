"""add waitlist to registrationstatusenum

Revision ID: 0746657dd317
Revises: b945a06e4bdd
Create Date: 2026-06-26 01:10:27.996549

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0746657dd317'
down_revision = 'b945a06e4bdd'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        # 1. Rename the old enum type
        op.execute("ALTER TYPE registrationstatusenum RENAME TO registrationstatusenum_old")
        # 2. Create the new enum type with waitlist, accepted, cancelled
        op.execute(
            "CREATE TYPE registrationstatusenum AS ENUM "
            "('waitlist', 'accepted', 'cancelled')"
        )
        # 3. Alter the status column to use the new type
        op.execute(
            "ALTER TABLE registrations ALTER COLUMN status "
            "TYPE registrationstatusenum USING status::text::registrationstatusenum"
        )
        # 4. Drop the old enum type
        op.execute("DROP TYPE registrationstatusenum_old")


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        # 1. Rename the current enum type
        op.execute("ALTER TYPE registrationstatusenum RENAME TO registrationstatusenum_old")
        # 2. Create the old enum type including 'registered'
        op.execute(
            "CREATE TYPE registrationstatusenum AS ENUM "
            "('registered', 'accepted', 'cancelled')"
        )
        # 3. Alter the status column back
        op.execute(
            "ALTER TABLE registrations ALTER COLUMN status "
            "TYPE registrationstatusenum USING status::text::registrationstatusenum"
        )
        # 4. Drop the renamed type
        op.execute("DROP TYPE registrationstatusenum_old")


