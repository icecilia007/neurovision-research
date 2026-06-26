"""Alterar idade para nascimento

Revision ID: f63800b574cd
Revises: 0b772bfe0146
Create Date: 2025-08-29 02:11:10.160750

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f63800b574cd'
down_revision: Union[str, None] = '0b772bfe0146'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
