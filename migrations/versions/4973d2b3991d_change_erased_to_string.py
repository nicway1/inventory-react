"""change_erased_to_string

Revision ID: 4973d2b3991d
Revises: add_tech_notes
Create Date: 2025-02-28 09:16:58.378776+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4973d2b3991d'
down_revision: Union[str, None] = 'add_tech_notes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert boolean values to strings first
    op.execute("UPDATE assets SET erased = CASE WHEN erased = 1 THEN 'completed' ELSE 'not completed' END")
    
    # Change column type to String
    with op.batch_alter_table('assets') as batch_op:
        batch_op.alter_column('erased',
                            existing_type=sa.Boolean(),
                            type_=sa.String(50),
                            existing_nullable=True)


def downgrade() -> None:
    # Convert string values back to boolean
    op.execute("UPDATE assets SET erased = CASE WHEN erased = 'completed' THEN 1 ELSE 0 END")
    
    # Change column type back to Boolean
    with op.batch_alter_table('assets') as batch_op:
        batch_op.alter_column('erased',
                            existing_type=sa.String(50),
                            type_=sa.Boolean(),
                            existing_nullable=True)
