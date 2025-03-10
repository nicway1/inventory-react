"""fix tech notes field

Revision ID: fix_tech_notes
Revises: 4973d2b3991d_change_erased_to_string
Create Date: 2024-03-05 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'fix_tech_notes'
down_revision = '4973d2b3991d_change_erased_to_string'
branch_labels = None
depends_on = None

def upgrade():
    # Get the database connection
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [col['name'] for col in inspector.get_columns('assets')]
    
    # Only add the column if it doesn't exist
    if 'tech_notes' not in columns:
        op.add_column('assets', sa.Column('tech_notes', sa.String(2000)))

def downgrade():
    # Get the database connection
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [col['name'] for col in inspector.get_columns('assets')]
    
    # Only drop the column if it exists
    if 'tech_notes' in columns:
        op.drop_column('assets', 'tech_notes') 