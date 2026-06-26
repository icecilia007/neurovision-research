"""data quality fixes

Fixes found while analysing test submission 122:

1. TR1 (attention check) had the wrong answer key: 'Perturbador' was marked
   is_correct, but the CHYPS instruction defines discomfort as *physical*
   ("Dor física, cansaço ou tensão dentro ou ao redor dos olhos ou da
   cabeça"), which is the option that proves the participant read it.
2. Option texts carried stray leading whitespace (all TR1 options, one QS6
   option) — cosmetic in the UI, ugly in reports/CSV exports.
3. The conditional medication question created by e4b8c2d6f1a3 had no
   caption, so reports showed a generated slug ('q43_qual_'). It is the 10th
   sociodemographic question -> caption 'QS10'. (e4b8c2d6f1a3 was amended to
   create it with the caption already; this covers databases where it had
   run before the amendment.)

Revision ID: b3d8f6a2e9c7
Revises: a7f2e9c4d1b5
Create Date: 2026-06-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'b3d8f6a2e9c7'
down_revision: Union[str, None] = 'a7f2e9c4d1b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. TR1 answer key: only the physical-discomfort option is correct.
    conn.execute(text("""
        UPDATE question_options
        SET is_correct = (TRIM(text) LIKE 'Dor física%')
        WHERE question_id IN (SELECT id FROM questions WHERE caption = 'TR1')
    """))

    # 2. Strip stray whitespace from every option text.
    conn.execute(text("""
        UPDATE question_options SET text = TRIM(text) WHERE text != TRIM(text)
    """))

    # 3. Caption for the conditional medication question (no-op when
    #    e4b8c2d6f1a3 already created it with the caption).
    conn.execute(text("""
        UPDATE questions SET caption = 'QS10'
        WHERE caption IS NULL
          AND depends_on_question_id IS NOT NULL
          AND text = 'Qual medicamento psiquiátrico você utiliza?'
          AND NOT EXISTS (SELECT 1 FROM questions WHERE caption = 'QS10')
    """))


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(text("""
        UPDATE questions SET caption = NULL WHERE caption = 'QS10'
    """))

    # Whitespace removal is intentionally not reverted.

    conn.execute(text("""
        UPDATE question_options
        SET is_correct = (TRIM(text) = 'Perturbador')
        WHERE question_id IN (SELECT id FROM questions WHERE caption = 'TR1')
    """))
