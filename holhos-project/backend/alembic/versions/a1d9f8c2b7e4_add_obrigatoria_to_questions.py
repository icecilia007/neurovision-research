"""add obrigatoria to questions

Revision ID: a1d9f8c2b7e4
Revises: b2d1f3c7a9e0
Create Date: 2026-04-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1d9f8c2b7e4'
down_revision: Union[str, None] = 'b2d1f3c7a9e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'questions',
        sa.Column('obrigatoria', sa.Boolean(), nullable=True, server_default=sa.text('true'))
    )
    op.execute('UPDATE questions SET obrigatoria = true WHERE obrigatoria IS NULL')
    op.alter_column('questions', 'obrigatoria', nullable=False)


def downgrade() -> None:
    op.drop_column('questions', 'obrigatoria')
