"""add term support

Revision ID: b2d1f3c7a9e0
Revises: 967df56bd26a
Create Date: 2026-03-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2d1f3c7a9e0'
down_revision: Union[str, None] = '967df56bd26a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('questions', sa.Column('titulo', sa.String(length=255), nullable=True))
    op.execute("ALTER TYPE itemtypeenum ADD VALUE IF NOT EXISTS 'term'")


def downgrade() -> None:
    op.drop_column('questions', 'titulo')
    # NOTE: Removing a value from a Postgres enum is non-trivial; leaving as-is.
