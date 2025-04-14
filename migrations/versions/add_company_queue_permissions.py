"""Add company_queue_permissions table

Revision ID: 675ed76a9bca
Revises: 5f33d8e62ace
Create Date: 2023-12-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '675ed76a9bca'
down_revision = '5f33d8e62ace'  # Update to point to one of the existing heads
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('company_queue_permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('queue_id', sa.Integer(), nullable=False),
        sa.Column('can_view', sa.Boolean(), nullable=True, default=True),
        sa.Column('can_create', sa.Boolean(), nullable=True, default=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['queue_id'], ['queues.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    # Add index for faster lookups
    op.create_index(op.f('ix_company_queue_permissions_company_id'), 'company_queue_permissions', ['company_id'], unique=False)
    op.create_index(op.f('ix_company_queue_permissions_queue_id'), 'company_queue_permissions', ['queue_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_company_queue_permissions_queue_id'), table_name='company_queue_permissions')
    op.drop_index(op.f('ix_company_queue_permissions_company_id'), table_name='company_queue_permissions')
    op.drop_table('company_queue_permissions') 