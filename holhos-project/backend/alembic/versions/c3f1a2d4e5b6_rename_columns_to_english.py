"""rename columns to english

Revision ID: c3f1a2d4e5b6
Revises: a1d9f8c2b7e4
Create Date: 2026-04-11 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c3f1a2d4e5b6'
down_revision: Union[str, None] = 'a1d9f8c2b7e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users
    op.alter_column('users', 'nome_completo', new_column_name='full_name')
    op.alter_column('users', 'genero', new_column_name='gender')
    op.alter_column('users', 'nascimento', new_column_name='birth_date')
    op.alter_column('users', 'escolaridade', new_column_name='education_level')
    op.alter_column('users', 'telefone', new_column_name='phone')
    op.alter_column('users', 'senha_hash', new_column_name='password_hash')

    # instructions
    op.alter_column('instructions', 'texto', new_column_name='text')

    # questions
    op.alter_column('questions', 'titulo', new_column_name='title')
    op.alter_column('questions', 'texto', new_column_name='text')
    op.alter_column('questions', 'tipo', new_column_name='question_type')
    op.alter_column('questions', 'obrigatoria', new_column_name='is_required')
    op.alter_column('questions', 'peso', new_column_name='weight')

    # question_options
    op.alter_column('question_options', 'texto', new_column_name='text')
    op.alter_column('question_options', 'ordem', new_column_name='sort_order')
    op.alter_column('question_options', 'peso', new_column_name='weight')

    # questionnaires
    op.alter_column('questionnaires', 'titulo', new_column_name='title')
    op.alter_column('questionnaires', 'descricao', new_column_name='description')
    op.alter_column('questionnaires', 'ativo', new_column_name='is_active')
    op.alter_column('questionnaires', 'criador_id', new_column_name='creator_id')

    # questionnaire_items
    op.alter_column('questionnaire_items', 'ordem', new_column_name='sort_order')


def downgrade() -> None:
    # questionnaire_items
    op.alter_column('questionnaire_items', 'sort_order', new_column_name='ordem')

    # questionnaires
    op.alter_column('questionnaires', 'creator_id', new_column_name='criador_id')
    op.alter_column('questionnaires', 'is_active', new_column_name='ativo')
    op.alter_column('questionnaires', 'description', new_column_name='descricao')
    op.alter_column('questionnaires', 'title', new_column_name='titulo')

    # question_options
    op.alter_column('question_options', 'weight', new_column_name='peso')
    op.alter_column('question_options', 'sort_order', new_column_name='ordem')
    op.alter_column('question_options', 'text', new_column_name='texto')

    # questions
    op.alter_column('questions', 'weight', new_column_name='peso')
    op.alter_column('questions', 'is_required', new_column_name='obrigatoria')
    op.alter_column('questions', 'question_type', new_column_name='tipo')
    op.alter_column('questions', 'text', new_column_name='texto')
    op.alter_column('questions', 'title', new_column_name='titulo')

    # instructions
    op.alter_column('instructions', 'text', new_column_name='texto')

    # users
    op.alter_column('users', 'password_hash', new_column_name='senha_hash')
    op.alter_column('users', 'phone', new_column_name='telefone')
    op.alter_column('users', 'education_level', new_column_name='escolaridade')
    op.alter_column('users', 'birth_date', new_column_name='nascimento')
    op.alter_column('users', 'gender', new_column_name='genero')
    op.alter_column('users', 'full_name', new_column_name='nome_completo')
