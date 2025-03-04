"""rebuild schema

Revision ID: rebuild_schema
Revises: merge_heads
Create Date: 2024-03-05 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'rebuild_schema'
down_revision = 'merge_heads'
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    
    # Create temporary tables with the correct schema
    op.create_table(
        'users_new',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=80), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=True),
        sa.Column('password_hash', sa.String(length=128), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
    )
    
    op.create_table(
        'assets_new',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_tag', sa.String(length=50), nullable=True),
        sa.Column('serial_num', sa.String(length=50), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('manufacturer', sa.String(length=100), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('cost_price', sa.Float(), nullable=True),
        sa.Column('location_id', sa.Integer(), nullable=True),
        sa.Column('company_id', sa.Integer(), nullable=True),
        sa.Column('specifications', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('tech_notes', sa.String(length=2000), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('assigned_to_id', sa.Integer(), nullable=True),
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('hardware_type', sa.String(length=50), nullable=True),
        sa.Column('inventory', sa.String(length=50), nullable=True),
        sa.Column('customer', sa.String(length=100), nullable=True),
        sa.Column('country', sa.String(length=50), nullable=True),
        sa.Column('asset_type', sa.String(length=50), nullable=True),
        sa.Column('receiving_date', sa.DateTime(), nullable=True),
        sa.Column('keyboard', sa.String(length=50), nullable=True),
        sa.Column('po', sa.String(length=50), nullable=True),
        sa.Column('erased', sa.String(length=50), nullable=True),
        sa.Column('condition', sa.String(length=50), nullable=True),
        sa.Column('diag', sa.String(length=50), nullable=True),
        sa.Column('cpu_type', sa.String(length=50), nullable=True),
        sa.Column('cpu_cores', sa.Integer(), nullable=True),
        sa.Column('gpu_cores', sa.Integer(), nullable=True),
        sa.Column('memory', sa.Integer(), nullable=True),
        sa.Column('harddrive', sa.Integer(), nullable=True),
        sa.Column('charger', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Copy data from old tables to new ones
    conn.execute(text('INSERT INTO users_new SELECT id, username, email, password_hash, role FROM users'))
    conn.execute(text('''
        INSERT INTO assets_new 
        SELECT id, asset_tag, serial_num, name, model, manufacturer, category, status, 
               cost_price, location_id, company_id, specifications, notes, tech_notes,
               created_at, updated_at, assigned_to_id, customer_id, hardware_type,
               inventory, customer, country, asset_type, receiving_date, keyboard,
               po, erased, condition, diag, cpu_type, cpu_cores, gpu_cores,
               memory, harddrive, charger
        FROM assets
    '''))
    
    # Drop old tables
    op.drop_table('users')
    op.drop_table('assets')
    
    # Rename new tables to original names
    op.rename_table('users_new', 'users')
    op.rename_table('assets_new', 'assets')

def downgrade():
    pass 