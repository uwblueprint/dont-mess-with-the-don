"""add confirmation requests table

Revision ID: 579decbd8763
Revises: b945a06e4bdd
Create Date: 2026-06-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision = '579decbd8763'
down_revision = 'b945a06e4bdd'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'confirmation_requests',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('registration_id', sa.Integer(), nullable=False),
        sa.Column('email_status', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('confirmation_time', sa.DateTime(), nullable=True),
        sa.Column('deadline', sa.DateTime(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['registration_id'], ['registrations.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('confirmation_requests')
