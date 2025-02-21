"""add repair ticket fields

Revision ID: 5f33d8e62ace
Revises: 
Create Date: 2024-03-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '5f33d8e62ace'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns to tickets table
    repair_status_enum = sa.Enum(
        'PENDING_ASSESSMENT',
        'PENDING_QUOTE',
        'QUOTE_PROVIDED',
        'REPAIR_APPROVED',
        'REPAIR_IN_PROGRESS',
        'REPAIR_COMPLETED',
        'PENDING_DISPOSAL',
        'DISPOSAL_APPROVED',
        'DISPOSAL_COMPLETED',
        name='repairstatus'
    )
    
    with op.batch_alter_table('tickets') as batch_op:
        batch_op.add_column(sa.Column('repair_status', repair_status_enum, nullable=True))
        batch_op.add_column(sa.Column('country', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('damage_description', sa.String(1000), nullable=True))
        batch_op.add_column(sa.Column('apple_diagnostics', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('image_path', sa.String(500), nullable=True))

def downgrade():
    # Remove the columns
    with op.batch_alter_table('tickets') as batch_op:
        batch_op.drop_column('repair_status')
        batch_op.drop_column('country')
        batch_op.drop_column('damage_description')
        batch_op.drop_column('apple_diagnostics')
        batch_op.drop_column('image_path')
    
    # Drop the enum type
    op.execute('DROP TYPE repairstatus')
