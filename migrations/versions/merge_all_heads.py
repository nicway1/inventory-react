"""merge all heads

Revision ID: merge_all_heads
Revises: 5f33d8e62ace, add_shipping_tracking_columns, make_email_nullable
Create Date: 2025-04-09 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_all_heads'
down_revision = None
branch_labels = None
depends_on = ('5f33d8e62ace', 'add_shipping_tracking_columns', 'make_email_nullable')

def upgrade():
    pass

def downgrade():
    pass 