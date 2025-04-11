"""add tracking history table

Revision ID: add_tracking_history_table
Revises: add_shipping_tracking_columns
Create Date: 2025-04-11 05:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'add_tracking_history_table'
down_revision = 'add_shipping_tracking_columns'
branch_labels = None
depends_on = None

def table_exists(table_name):
    """Check if a table exists in the database"""
    conn = op.get_bind()
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()

def upgrade():
    # Create tracking_history table if it doesn't exist
    if not table_exists('tracking_history'):
        op.create_table(
            'tracking_history',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('tracking_number', sa.String(100), nullable=False, index=True),
            sa.Column('carrier', sa.String(50), nullable=True),
            sa.Column('status', sa.String(100), nullable=True),
            sa.Column('last_updated', sa.DateTime(), nullable=True),
            sa.Column('tracking_data', sa.Text(), nullable=True),
            sa.Column('ticket_id', sa.Integer(), nullable=True),
            sa.Column('tracking_type', sa.String(20), nullable=True),
            sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create index on tracking_number for faster lookups
        op.create_index('ix_tracking_history_tracking_number', 'tracking_history', ['tracking_number'])

def downgrade():
    # Drop the tracking_history table if it exists
    if table_exists('tracking_history'):
        op.drop_index('ix_tracking_history_tracking_number', 'tracking_history')
        op.drop_table('tracking_history') 