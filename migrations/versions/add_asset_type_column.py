"""add asset_type column to assets table

Revision ID: add_asset_type_column
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('assets', sa.Column('asset_type', sa.String(100), nullable=True))

def downgrade():
    op.drop_column('assets', 'asset_type') 