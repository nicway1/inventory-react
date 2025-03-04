"""fix all columns

Revision ID: fix_all_columns
Revises: add_user_role
Create Date: 2024-03-05 09:35:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'fix_all_columns'
down_revision = 'add_user_role'
branch_labels = None
depends_on = None

def upgrade():
    # Get the database connection
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    # Check and add columns for users table
    users_columns = [col['name'] for col in inspector.get_columns('users')]
    if 'role' not in users_columns:
        op.add_column('users', sa.Column('role', sa.String(50)))
    
    # Check and add columns for assets table
    assets_columns = [col['name'] for col in inspector.get_columns('assets')]
    if 'tech_notes' not in assets_columns:
        op.add_column('assets', sa.Column('tech_notes', sa.String(2000)))
    if 'erased' in assets_columns:
        # First create a new column with _new suffix
        op.add_column('assets', sa.Column('erased_new', sa.String(50)))
        # Copy data from old column to new column
        conn.execute('UPDATE assets SET erased_new = CAST(erased AS TEXT)')
        # Drop the old column
        op.drop_column('assets', 'erased')
        # Rename the new column to the original name
        op.alter_column('assets', 'erased_new', new_column_name='erased')
    else:
        op.add_column('assets', sa.Column('erased', sa.String(50)))

def downgrade():
    # Get the database connection
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    # Check and remove columns from assets table
    assets_columns = [col['name'] for col in inspector.get_columns('assets')]
    if 'tech_notes' in assets_columns:
        op.drop_column('assets', 'tech_notes')
    if 'erased' in assets_columns:
        op.drop_column('assets', 'erased')
    
    # Check and remove columns from users table
    users_columns = [col['name'] for col in inspector.get_columns('users')]
    if 'role' in users_columns:
        op.drop_column('users', 'role') 