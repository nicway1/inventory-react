"""merge heads

Revision ID: merge_heads
Revises: 4973d2b3991d, fix_all_columns
Create Date: 2024-03-05 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_heads'
down_revision = ('4973d2b3991d', 'fix_all_columns')
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    pass 