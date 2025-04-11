"""add shipping tracking columns

Revision ID: add_shipping_tracking_columns
Revises: final_schema_fix
Create Date: 2025-04-09 01:55:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'add_shipping_tracking_columns'
down_revision = 'final_schema_fix'
branch_labels = None
depends_on = None

def column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def upgrade():
    # Add second tracking info columns for Asset Checkout
    with op.batch_alter_table('tickets') as batch_op:
        # Only add columns if they don't exist
        if not column_exists('tickets', 'shipping_tracking_2'):
            batch_op.add_column(sa.Column('shipping_tracking_2', sa.String(100), nullable=True))
        
        if not column_exists('tickets', 'shipping_carrier_2'):
            batch_op.add_column(sa.Column('shipping_carrier_2', sa.String(50), nullable=True))
        
        if not column_exists('tickets', 'shipping_status_2'):
            batch_op.add_column(sa.Column('shipping_status_2', sa.String(100), nullable=True))

def downgrade():
    # Remove columns in reverse order
    with op.batch_alter_table('tickets') as batch_op:
        if column_exists('tickets', 'shipping_status_2'):
            batch_op.drop_column('shipping_status_2')
        
        if column_exists('tickets', 'shipping_carrier_2'):
            batch_op.drop_column('shipping_carrier_2')
        
        if column_exists('tickets', 'shipping_tracking_2'):
            batch_op.drop_column('shipping_tracking_2') 