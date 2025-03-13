"""make email nullable

Revision ID: make_email_nullable
Revises: add_user_role
Create Date: 2024-02-21 08:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'make_email_nullable'
down_revision = 'add_user_role'
branch_labels = None
depends_on = None

def upgrade():
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table('customer_users') as batch_op:
        # Drop the existing email column
        batch_op.drop_column('email')
        # Re-create it as nullable
        batch_op.add_column(sa.Column('email', sa.String(100), nullable=True))

def downgrade():
    # Revert changes
    with op.batch_alter_table('customer_users') as batch_op:
        # Drop the nullable email column
        batch_op.drop_column('email')
        # Re-create it as non-nullable
        batch_op.add_column(sa.Column('email', sa.String(100), nullable=False)) 