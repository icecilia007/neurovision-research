"""add steps and conditional questions

Adds the generic building blocks for multi-step questionnaires and
conditional (branching) questions, then backfills the existing CHYPS-V BR
production questionnaire so it works without UI re-editing (it already has
responses and therefore cannot be edited through the creation page):

- questionnaire_items.step: which step of the flow each item belongs to
- questionnaires.step_labels: JSON list with the display name of each step
- questions.depends_on_question_id / depends_on_option_id: show a question
  only when a specific option of another question is selected

Revision ID: e4b8c2d6f1a3
Revises: c3f1a2d4e5b6
Create Date: 2026-06-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'e4b8c2d6f1a3'
down_revision: Union[str, None] = 'c3f1a2d4e5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CHYPS_CAPTIONS = tuple(f"Q{i}" for i in range(1, 21))

STEP_LABELS = [
    "Termo de Consentimento",
    "Questionário Sociodemográfico",
    "Teste CHYPS-V BR",
    "Avaliação do Teste CHYPS-V BR",
]


def upgrade() -> None:
    # ── Schema ────────────────────────────────────────────────────────────────
    op.add_column(
        'questionnaire_items',
        sa.Column('step', sa.Integer(), nullable=False, server_default='1')
    )
    op.add_column(
        'questionnaires',
        sa.Column('step_labels', sa.JSON(), nullable=True)
    )
    op.add_column(
        'questions',
        sa.Column('depends_on_question_id', sa.Integer(),
                  sa.ForeignKey('questions.id'), nullable=True)
    )
    op.add_column(
        'questions',
        sa.Column('depends_on_option_id', sa.Integer(),
                  sa.ForeignKey('question_options.id'), nullable=True)
    )

    # ── Backfill: CHYPS-V BR production questionnaire ────────────────────────
    conn = op.get_bind()

    chyps_questionnaires = conn.execute(text("""
        SELECT DISTINCT qi.questionnaire_id
        FROM questionnaire_items qi
        JOIN questions q ON qi.item_id = q.id AND qi.item_type = 'question'
        WHERE q.caption = ANY(:captions)
    """), {"captions": list(CHYPS_CAPTIONS)}).fetchall()

    for (questionnaire_id,) in chyps_questionnaires:
        _backfill_questionnaire_steps(conn, questionnaire_id)
        _backfill_medication_conditional(conn, questionnaire_id)


def _backfill_questionnaire_steps(conn, questionnaire_id: int) -> None:
    bounds = conn.execute(text("""
        SELECT MIN(qi.sort_order), MAX(qi.sort_order)
        FROM questionnaire_items qi
        JOIN questions q ON qi.item_id = q.id AND qi.item_type = 'question'
        WHERE qi.questionnaire_id = :qid AND q.caption = ANY(:captions)
    """), {"qid": questionnaire_id, "captions": list(CHYPS_CAPTIONS)}).fetchone()

    first_chyps, last_chyps = bounds

    # Terms always belong to the consent step
    conn.execute(text("""
        UPDATE questionnaire_items SET step = 1
        WHERE questionnaire_id = :qid AND item_type = 'term'
    """), {"qid": questionnaire_id})

    # Sociodemographic: anything (non-term) before the first CHYPS item
    conn.execute(text("""
        UPDATE questionnaire_items SET step = 2
        WHERE questionnaire_id = :qid AND item_type != 'term'
          AND sort_order < :first_chyps
    """), {"qid": questionnaire_id, "first_chyps": first_chyps})

    # CHYPS-V BR test: the Q1–Q20 block, including instructions placed in it
    conn.execute(text("""
        UPDATE questionnaire_items SET step = 3
        WHERE questionnaire_id = :qid AND item_type != 'term'
          AND sort_order BETWEEN :first_chyps AND :last_chyps
    """), {"qid": questionnaire_id, "first_chyps": first_chyps, "last_chyps": last_chyps})

    # Test evaluation: anything after the last CHYPS item
    conn.execute(text("""
        UPDATE questionnaire_items SET step = 4
        WHERE questionnaire_id = :qid AND item_type != 'term'
          AND sort_order > :last_chyps
    """), {"qid": questionnaire_id, "last_chyps": last_chyps})

    conn.execute(
        sa.text("UPDATE questionnaires SET step_labels = :labels WHERE id = :qid")
        .bindparams(sa.bindparam("labels", type_=sa.JSON())),
        {"qid": questionnaire_id, "labels": STEP_LABELS},
    )


def _backfill_medication_conditional(conn, questionnaire_id: int) -> None:
    """Wire the 'which medication?' follow-up to the psychiatric-medication
    question, shown only when the participant answers 'Sim'."""
    medication = conn.execute(text("""
        SELECT q.id, qi.sort_order, qi.step
        FROM questionnaire_items qi
        JOIN questions q ON qi.item_id = q.id AND qi.item_type = 'question'
        WHERE qi.questionnaire_id = :qid
          AND LOWER(q.text) LIKE '%medicamento psiquiátric%'
          AND q.question_type = 'single'
        LIMIT 1
    """), {"qid": questionnaire_id}).fetchone()

    if not medication:
        return

    medication_qid, medication_sort, medication_step = medication

    sim_option = conn.execute(text("""
        SELECT id FROM question_options
        WHERE question_id = :qid AND LOWER(TRIM(text)) LIKE 'sim%'
        ORDER BY sort_order
        LIMIT 1
    """), {"qid": medication_qid}).fetchone()

    if not sim_option:
        return

    existing = conn.execute(text("""
        SELECT q.id FROM questions q
        WHERE q.depends_on_question_id = :qid
        LIMIT 1
    """), {"qid": medication_qid}).fetchone()

    if existing:
        return

    detail_id = conn.execute(text("""
        INSERT INTO questions
            (caption, text, question_type, is_required, weight,
             depends_on_question_id, depends_on_option_id)
        VALUES
            ('QS10', 'Qual medicamento psiquiátrico você utiliza?', 'free_text', false, 1.0,
             :depends_qid, :depends_oid)
        RETURNING id
    """), {
        "depends_qid": medication_qid,
        "depends_oid": sim_option[0],
    }).fetchone()[0]

    # Place it right after the medication question, in the same step
    conn.execute(text("""
        UPDATE questionnaire_items
        SET sort_order = sort_order + 1
        WHERE questionnaire_id = :qid AND sort_order > :after
    """), {"qid": questionnaire_id, "after": medication_sort})

    conn.execute(text("""
        INSERT INTO questionnaire_items
            (questionnaire_id, item_type, item_id, sort_order, step)
        VALUES
            (:qid, 'question', :item_id, :sort_order, :step)
    """), {
        "qid": questionnaire_id,
        "item_id": detail_id,
        "sort_order": medication_sort + 1,
        "step": medication_step,
    })


def downgrade() -> None:
    conn = op.get_bind()

    # Remove backfilled conditional questions (and their answers/items)
    conditional_questions = conn.execute(text("""
        SELECT id FROM questions WHERE depends_on_question_id IS NOT NULL
    """)).fetchall()

    for (question_id,) in conditional_questions:
        conn.execute(
            text("DELETE FROM answers WHERE question_id = :id"),
            {"id": question_id}
        )
        conn.execute(text("""
            DELETE FROM questionnaire_items
            WHERE item_id = :id AND item_type = 'question'
        """), {"id": question_id})
        conn.execute(
            text("DELETE FROM questions WHERE id = :id"),
            {"id": question_id}
        )

    op.drop_column('questions', 'depends_on_option_id')
    op.drop_column('questions', 'depends_on_question_id')
    op.drop_column('questionnaires', 'step_labels')
    op.drop_column('questionnaire_items', 'step')
