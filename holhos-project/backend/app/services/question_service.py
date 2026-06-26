from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Dict, Any
from app.models.question import Question, QuestionOption
from app.schemas.question import QuestionCreate, QuestionOptionCreate
import sys

class QuestionService:
    
    def create_question(self, db: Session, question_data: QuestionCreate) -> Question:
        try:
            if question_data.caption:
                existing_question = db.query(Question).filter(
                    Question.caption == question_data.caption
                ).first()
                if existing_question:
                    raise ValueError(f"Caption '{question_data.caption}' já está em uso")

            db_question = Question(
                caption=question_data.caption,
                title=question_data.titulo,
                text=question_data.texto,
                question_type=question_data.tipo,
                is_required=bool(question_data.obrigatoria) if question_data.tipo == "free_text" else True,
                weight=question_data.peso,
                depends_on_question_id=question_data.depends_on_question_id,
                depends_on_option_id=question_data.depends_on_option_id
            )
            db.add(db_question)
            db.commit()
            db.refresh(db_question)

            if question_data.options:
                for option_data in question_data.options:
                    db_option = QuestionOption(
                        question_id=db_question.id,
                        text=option_data.texto,
                        sort_order=option_data.ordem,
                        is_correct=option_data.is_correct,
                        weight=option_data.peso
                    )
                    db.add(db_option)
                
                db.commit()
                db.refresh(db_question)

            return db_question
        
        except IntegrityError as e:
            db.rollback()
            error_msg = str(e).lower()
            
            if "unique" in error_msg or "duplicate" in error_msg or "caption" in error_msg:
                raise ValueError(f"Pergunta com caption '{question_data.caption}' já existe")
            else:
                raise ValueError(f"Erro de integridade ao criar pergunta: {error_msg}")
        
        except ValueError:
            db.rollback()
            raise
        
        except Exception as e:
            db.rollback()
            raise ValueError(f"Erro ao criar pergunta: {str(e)}")


    def get_question_by_id(self, db: Session, question_id: int) -> Question:
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise ValueError("Pergunta não encontrada")
        return question

    def get_question_by_caption(self, db: Session, caption: str) -> Question:
        question = db.query(Question).filter(Question.caption == caption).first()
        if not question:
            raise ValueError(f"Pergunta com caption '{caption}' não encontrada")
        return question

    def add_option_to_question(self, db: Session, question_id: int,
                              option_data: QuestionOptionCreate) -> QuestionOption:
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise ValueError("Pergunta não encontrada")

        db_option = QuestionOption(
            question_id=question_id,
            text=option_data.texto,
            sort_order=option_data.ordem,
            is_correct=option_data.is_correct,
            weight=option_data.peso
        )
        db.add(db_option)
        db.commit()
        db.refresh(db_option)
        return db_option

    def list_questions(self, db: Session, skip: int = 0, limit: int = 100) -> List[Question]:
        return db.query(Question).offset(skip).limit(limit).all()

    def delete_question(self, db: Session, question_id: int) -> bool:
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise ValueError("Pergunta não encontrada")
        db.delete(question)
        db.commit()
        return True

    def update_question(self, db: Session, question_id: int, question_data: Dict[str, Any]) -> Question: 

        
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise ValueError("Pergunta não encontrada")

        if 'texto' in question_data:
            question.text = question_data['texto']

        if 'titulo' in question_data:
            question.title = question_data['titulo']
            
        if 'tipo' in question_data:
            question.question_type = question_data['tipo']

        if 'obrigatoria' in question_data and question.question_type == 'free_text':
            question.is_required = bool(question_data['obrigatoria'])
        elif question.question_type != 'free_text':
            question.is_required = True
            
        if 'peso' in question_data:
            question.weight = question_data['peso']

        if 'depends_on_question_id' in question_data:
            question.depends_on_question_id = question_data['depends_on_question_id']

        if 'depends_on_option_id' in question_data:
            question.depends_on_option_id = question_data['depends_on_option_id']

        db.commit()

        if 'options' in question_data:
            
            db.query(QuestionOption).filter(QuestionOption.question_id == question_id).delete()
            db.commit()
            
            for option_data in question_data['options']:
                db_option = QuestionOption(
                    question_id=question_id,
                    text=option_data.get('texto'),
                    sort_order=option_data.get('ordem'),
                    is_correct=option_data.get('is_correct', False),
                    weight=option_data.get('peso', 0.0)
                )
                db.add(db_option)
            db.commit()

        db.refresh(question)
        
        return question
