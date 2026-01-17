"""Add category column to transaction

Revision ID: 0001_add_category
Revises: 0000_initial
Create Date: 2026-01-16 00:00:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_add_category'
down_revision = '0000_initial'
branch_labels = None
depends_on = None


def upgrade():
    # Add category column to transaction table
    op.add_column('transaction', sa.Column('category', sa.String(), nullable=True))


def downgrade():
    op.drop_column('transaction', 'category')
