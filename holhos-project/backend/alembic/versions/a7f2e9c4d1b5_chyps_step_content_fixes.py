"""chyps step and content fixes

Data-only fixes for the CHYPS-V BR production questionnaire, requested after
reviewing the multi-step flow:

1. The test instruction ("Este questionário pergunta se determinadas
   situações...") and the attention-check question TR1 belong to the CHYPS-V
   test step, not the sociodemographic step. They keep their sort_order, so
   they render at the top of the test page, right before Q1.
2. The sociodemographic instruction gains a short paragraph explaining that
   the collected data serve sample characterization and scale validation
   (mirroring how Price, Sumner & Powell, 2025, collected demographics and
   clinical data alongside the CHYPS for transdiagnostic validation).
3. F1 wording: the difficulty question must refer to the *test*, not the
   whole questionnaire.
4. F2 accent fix: "Observacao" -> "Observação".

All statements are guarded so the migration is idempotent and a no-op on
databases without this content.

Revision ID: a7f2e9c4d1b5
Revises: e4b8c2d6f1a3
Create Date: 2026-06-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'a7f2e9c4d1b5'
down_revision: Union[str, None] = 'e4b8c2d6f1a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEST_INSTRUCTION_PREFIX = 'Este questionário pergunta se determinadas situações%'
SOCIO_INSTRUCTION_PREFIX = 'Questionário sociodemográfico.%'

VALIDATION_PARAGRAPH = (
    'As perguntas a seguir coletam informações sociodemográficas e de saúde com a '
    'finalidade exclusiva de caracterizar a amostra e apoiar a validação da escala '
    'no contexto brasileiro. Esses dados permitem verificar se o instrumento se '
    'comporta de forma consistente entre diferentes grupos de participantes. '
    'Eles não influenciam sua pontuação no teste e são tratados de forma confidencial.'
)


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Move the test instruction and the attention check (TR1) to the
    #    CHYPS-V test step (3). sort_order is untouched, so both render at
    #    the top of the test page.
    conn.execute(text("""
        UPDATE questionnaire_items SET step = 3
        WHERE item_type = 'instruction'
          AND item_id IN (SELECT id FROM instructions WHERE text LIKE :prefix)
          AND step = 2
    """), {"prefix": TEST_INSTRUCTION_PREFIX})

    conn.execute(text("""
        UPDATE questionnaire_items SET step = 3
        WHERE item_type = 'question'
          AND item_id IN (SELECT id FROM questions WHERE caption = 'TR1')
          AND step = 2
    """))

    # 2. Add the research-validation paragraph to the sociodemographic
    #    instruction (between the heading and the LGPD paragraph).
    conn.execute(text("""
        UPDATE instructions
        SET text = REPLACE(
            text,
            'Questionário sociodemográfico.',
            'Questionário sociodemográfico.' || chr(10) || chr(10) || :paragraph
        )
        WHERE text LIKE :prefix
          AND text NOT LIKE '%caracterizar a amostra%'
    """), {"paragraph": VALIDATION_PARAGRAPH, "prefix": SOCIO_INSTRUCTION_PREFIX})

    # 3. The difficulty question refers specifically to the test.
    conn.execute(text("""
        UPDATE questions
        SET text = REPLACE(text, 'responder este questionário?', 'responder este teste?')
        WHERE caption = 'F1' AND text LIKE '%responder este questionário?%'
    """))

    # 4. Accent fix on F2.
    conn.execute(text("""
        UPDATE questions
        SET title = REPLACE(title, 'Observacao', 'Observação'),
            text  = REPLACE(text,  'Observacao', 'Observação')
        WHERE caption = 'F2'
    """))


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(text("""
        UPDATE questions
        SET title = REPLACE(title, 'Observação', 'Observacao'),
            text  = REPLACE(text,  'Observação', 'Observacao')
        WHERE caption = 'F2'
    """))

    conn.execute(text("""
        UPDATE questions
        SET text = REPLACE(text, 'responder este teste?', 'responder este questionário?')
        WHERE caption = 'F1' AND text LIKE '%responder este teste?%'
    """))

    conn.execute(text("""
        UPDATE instructions
        SET text = REPLACE(text, chr(10) || chr(10) || :paragraph, '')
        WHERE text LIKE :prefix
    """), {"paragraph": VALIDATION_PARAGRAPH, "prefix": SOCIO_INSTRUCTION_PREFIX})

    conn.execute(text("""
        UPDATE questionnaire_items SET step = 2
        WHERE item_type = 'question'
          AND item_id IN (SELECT id FROM questions WHERE caption = 'TR1')
          AND step = 3
    """))

    conn.execute(text("""
        UPDATE questionnaire_items SET step = 2
        WHERE item_type = 'instruction'
          AND item_id IN (SELECT id FROM instructions WHERE text LIKE :prefix)
          AND step = 3
    """), {"prefix": TEST_INSTRUCTION_PREFIX})
