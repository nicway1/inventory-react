"""add user role column

Revision ID: add_user_role
Revises: add_tech_notes
Create Date: 2024-02-21 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_user_role'
down_revision = 'add_tech_notes'
branch_labels = None
depends_on = None

def upgrade():
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('role', sa.String(50), nullable=True))

def downgrade():
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('role') 