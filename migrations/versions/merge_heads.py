"""merge heads

Revision ID: merge_heads
Revises: add_asset_transactions
Create Date: 2024-03-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_heads'
down_revision = 'add_asset_transactions'
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    pass 