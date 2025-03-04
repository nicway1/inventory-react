"""add tech notes field

Revision ID: add_tech_notes
Revises: add_user_role
Create Date: 2024-02-28 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_tech_notes'
down_revision = 'add_user_role'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('assets', sa.Column('tech_notes', sa.String(2000)))

def downgrade():
    op.drop_column('assets', 'tech_notes') 