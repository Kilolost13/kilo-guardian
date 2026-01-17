"""Initial schema

Revision ID: 0000_initial
Revises: 
Create Date: 2026-01-14 00:00:00
Updated: 2026-01-16 - Added category column to transaction table
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0000_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create transaction table
    op.create_table(
        'transaction',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('date', sa.String(), nullable=False),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create receiptitem table
    op.create_table(
        'receiptitem',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('category', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create reminder table
    op.create_table(
        'reminder',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('text', sa.String(), nullable=False),
        sa.Column('when', sa.String(), nullable=False),
        sa.Column('sent', sa.Boolean(), nullable=False),
        sa.Column('recurrence', sa.String(), nullable=True),
        sa.Column('timezone', sa.String(), nullable=True),
        sa.Column('preset_id', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create reminderpreset table
    op.create_table(
        'reminderpreset',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('time_of_day', sa.String(), nullable=True),
        sa.Column('recurrence', sa.String(), nullable=True),
        sa.Column('tags', sa.String(), nullable=True),
        sa.Column('habit_id', sa.Integer(), nullable=True),
        sa.Column('med_id', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('reminderpreset')
    op.drop_table('reminder')
    op.drop_table('receiptitem')
    op.drop_table('transaction')
