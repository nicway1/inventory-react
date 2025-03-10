"""final schema fix

Revision ID: final_schema_fix
Revises: merge_heads
Create Date: 2024-03-05 10:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'final_schema_fix'
down_revision = 'merge_heads'
branch_labels = None
depends_on = None

def upgrade():
    # Get the database connection
    conn = op.get_bind()
    
    # Get existing columns
    inspector = sa.inspect(conn)
    
    def column_exists(table_name, column_name):
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    
    # Safely add columns if they don't exist
    try:
        if not column_exists('users', 'role'):
            op.add_column('users', sa.Column('role', sa.String(50)))
    except Exception as e:
        print(f"Note: Could not add role column: {e}")
    
    try:
        if not column_exists('assets', 'tech_notes'):
            op.add_column('assets', sa.Column('tech_notes', sa.String(2000)))
    except Exception as e:
        print(f"Note: Could not add tech_notes column: {e}")
    
    # Handle the erased column conversion
    try:
        if column_exists('assets', 'erased'):
            # Check if erased is already a string type
            erased_type = next(col['type'] for col in inspector.get_columns('assets') if col['name'] == 'erased')
            if not isinstance(erased_type, sa.String):
                # Create new column
                if not column_exists('assets', 'erased_new'):
                    op.add_column('assets', sa.Column('erased_new', sa.String(50)))
                # Copy and convert data
                conn.execute(text('UPDATE assets SET erased_new = CAST(erased AS TEXT)'))
                # Drop old column and rename new one
                op.drop_column('assets', 'erased')
                op.alter_column('assets', 'erased_new', new_column_name='erased')
    except Exception as e:
        print(f"Note: Could not convert erased column: {e}")

def downgrade():
    pass 