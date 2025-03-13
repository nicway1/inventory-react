"""Add asset transactions table

Revision ID: add_asset_transactions
Revises: final_schema_fix
Create Date: 2024-03-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_asset_transactions'
down_revision = 'final_schema_fix'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'asset_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_number', sa.String(length=50), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('transaction_date', sa.DateTime(), nullable=False),
        sa.Column('transaction_type', sa.String(length=50), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ),
        sa.ForeignKeyConstraint(['customer_id'], ['customer_users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('transaction_number')
    )

def downgrade():
    op.drop_table('asset_transactions') 