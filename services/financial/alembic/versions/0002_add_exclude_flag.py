"""Add exclude_from_balance flag

Revision ID: 0002_add_exclude_flag
Revises: 0001_add_category
Create Date: 2026-01-16

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002_add_exclude_flag'
down_revision = '0001_add_category'
branch_labels = None
depends_on = None


def upgrade():
    # Add exclude_from_balance column with default False
    op.add_column('transaction', sa.Column('exclude_from_balance', sa.Boolean(), nullable=True))
    # Set default value for existing rows
    op.execute('UPDATE "transaction" SET exclude_from_balance = 0 WHERE exclude_from_balance IS NULL')


def downgrade():
    op.drop_column('transaction', 'exclude_from_balance')
