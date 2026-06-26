from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Dict, Any
from app.models import Questionnaire, QuestionnaireItem, Question, QuestionOption, Instruction, QuestionnaireSubmission, Answer
from app.schemas.questionnaire import (
    QuestionnaireCreate, QuestionnaireItemForResponse,
    QuestionnaireForResponse, GenerateLinkResponse
)
from app.schemas.question import QuestionForResponse, QuestionOptionResponse
from app.schemas.instruction import InstructionCreate, InstructionResponse
from app.utils.crypto import encrypt_questionnaire_id, decrypt_questionnaire_id
from app.config import settings
import random
import sys

class QuestionnaireService:
    
    def create_instruction(self, db: Session, instruction_data: InstructionCreate) -> Instruction:
        db_instruction = Instruction(text=instruction_data.texto)
        db.add(db_instruction)
        db.commit()
        db.refresh(db_instruction)
        return db_instruction

    def create_questionnaire(self, db: Session, questionnaire_data: QuestionnaireCreate) -> Questionnaire:
        try:
            db_questionnaire = Questionnaire(
                title=questionnaire_data.titulo,
                description=questionnaire_data.descricao,
                question_order=questionnaire_data.question_order,
                step_labels=questionnaire_data.step_labels,
                creator_id=questionnaire_data.criador_id
            )
            db.add(db_questionnaire)
            db.commit()
            db.refresh(db_questionnaire)

            for item in questionnaire_data.items:
                db_item = QuestionnaireItem(
                    questionnaire_id=db_questionnaire.id,
                    item_type=item.item_type,
                    item_id=item.item_id,
                    sort_order=item.ordem,
                    step=item.step
                )
                db.add(db_item)
            
            db.commit()
            return db_questionnaire
        
        except IntegrityError as e:
            db.rollback()
            error_msg = str(e).lower()
            
            if "identificador" in error_msg or "unique" in error_msg:
                raise ValueError("Este identificador já existe. Por favor, use um identificador único.")
            else:
                raise ValueError("Erro ao criar o questionário. Verifique os dados.")
        
        except ValueError:
            db.rollback()
            raise
        
        except Exception as e:
            db.rollback()
            raise ValueError(f"Erro ao criar questionário: {str(e)}")


    def generate_questionnaire_link(self, db: Session, questionnaire_id: int) -> GenerateLinkResponse:
        questionnaire = db.query(Questionnaire).filter(Questionnaire.id == questionnaire_id).first()
        if not questionnaire:
            raise ValueError("Questionário não encontrado")
        
        encrypted_id = encrypt_questionnaire_id(questionnaire_id)
        link = f"{settings.frontend_base_url}/questionnaire/{encrypted_id}/respond"
        
        return GenerateLinkResponse(
            questionnaire_id=questionnaire_id,
            link=link
        )

    def get_questionnaire_for_response(self, db: Session, questionnaire_id_param: str) -> QuestionnaireForResponse:
        try:
            questionnaire_id = decrypt_questionnaire_id(questionnaire_id_param)
        except ValueError:
            raise ValueError("ID do questionário inválido")

        questionnaire = db.query(Questionnaire).filter(Questionnaire.id == questionnaire_id).first()
        if not questionnaire:
            raise ValueError("Questionário não encontrado")

        items_query = db.query(QuestionnaireItem).filter(
            QuestionnaireItem.questionnaire_id == questionnaire_id
        )

        if questionnaire.question_order == "ascending":
            items_query = items_query.order_by(QuestionnaireItem.sort_order.asc())
        elif questionnaire.question_order == "descending":
            items_query = items_query.order_by(QuestionnaireItem.sort_order.desc())
        elif questionnaire.question_order == "custom":
            items_query = items_query.order_by(QuestionnaireItem.sort_order.asc())
        elif questionnaire.question_order == "random":
            items_query = items_query.order_by(QuestionnaireItem.id)

        items = items_query.all()

        if questionnaire.question_order == "random":
            random.shuffle(items)

        response_items = []
        for item in items:
            if item.item_type in ("question", "term"):
                question = db.query(Question).filter(Question.id == item.item_id).first()
                if question:
                    options_query = db.query(QuestionOption).filter(
                        QuestionOption.question_id == question.id
                    )

                    if questionnaire.question_order == "random":
                        options = options_query.all()
                        random.shuffle(options)
                    else:
                        options = options_query.order_by(QuestionOption.sort_order.asc()).all()

                    question_response = QuestionForResponse(
                        id=question.id,
                        caption=question.caption,
                        titulo=getattr(question, "title", None),
                        texto=question.text,
                        tipo=question.question_type,
                        obrigatoria=getattr(question, "is_required", True),
                        peso=question.weight,
                        depends_on_question_id=getattr(question, "depends_on_question_id", None),
                        depends_on_option_id=getattr(question, "depends_on_option_id", None),
                        options=[QuestionOptionResponse.from_orm(opt) for opt in options]
                    )

                    response_items.append(QuestionnaireItemForResponse(
                        tipo=item.item_type,
                        ordem=item.sort_order,
                        step=getattr(item, "step", 1) or 1,
                        content=question_response
                    ))

            elif item.item_type == "instruction":
                instruction = db.query(Instruction).filter(Instruction.id == item.item_id).first()
                if instruction:
                    response_items.append(QuestionnaireItemForResponse(
                        tipo=item.item_type,
                        ordem=item.sort_order,
                        step=getattr(item, "step", 1) or 1,
                        content=InstructionResponse.from_orm(instruction)
                    ))

        return QuestionnaireForResponse(
            id=questionnaire.id,
            titulo=questionnaire.title,
            descricao=questionnaire.description,
            question_order=questionnaire.question_order.value,
            step_labels=questionnaire.step_labels,
            items=response_items
        )

    def list_questionnaires(self, db: Session, skip: int = 0, limit: int = 100) -> List[Questionnaire]:
        return db.query(Questionnaire).offset(skip).limit(limit).all()

    def list_questionnaires_by_creator(self, db: Session, criador_id: int) -> List[Questionnaire]:
        return db.query(Questionnaire).filter(Questionnaire.creator_id == criador_id).all()

    def get_questionnaire_by_id(self, db: Session, questionnaire_id: int) -> Questionnaire:
        questionnaire = db.query(Questionnaire).filter(Questionnaire.id == questionnaire_id).first()
        if not questionnaire:
            raise ValueError("Questionário não encontrado")
        return questionnaire

    def delete_questionnaire(self, db: Session, questionnaire_id: int) -> bool:
        try:
            questionnaire = db.query(Questionnaire).filter(
                Questionnaire.id == questionnaire_id
            ).first()
            
            if not questionnaire:
                raise ValueError("Questionário não encontrado")
            
            submissions = db.query(QuestionnaireSubmission).filter(
                QuestionnaireSubmission.questionnaire_id == questionnaire_id
            ).all()
            
            submission_ids = [s.id for s in submissions]
            
            if submission_ids:
                db.query(Answer).filter(
                    Answer.submission_id.in_(submission_ids)
                ).delete(synchronize_session=False)
            
            db.query(QuestionnaireSubmission).filter(
                QuestionnaireSubmission.questionnaire_id == questionnaire_id
            ).delete(synchronize_session=False)
            
            questions = db.query(Question).select_from(Question).join(
                QuestionnaireItem,
                Question.id == QuestionnaireItem.item_id
            ).filter(
                QuestionnaireItem.questionnaire_id == questionnaire_id,
                QuestionnaireItem.item_type.in_(["question", "term"])
            ).all()
            
            question_ids = [q.id for q in questions]
            
            if question_ids:
                db.query(QuestionOption).filter(
                    QuestionOption.question_id.in_(question_ids)
                ).delete(synchronize_session=False)
                
                db.query(Question).filter(
                    Question.id.in_(question_ids)
                ).delete(synchronize_session=False)
            
            instructions = db.query(Instruction).select_from(Instruction).join(
                QuestionnaireItem,
                Instruction.id == QuestionnaireItem.item_id
            ).filter(
                QuestionnaireItem.questionnaire_id == questionnaire_id,
                QuestionnaireItem.item_type == "instruction"
            ).all()
            
            instruction_ids = [i.id for i in instructions]
            
            if instruction_ids:
                db.query(Instruction).filter(
                    Instruction.id.in_(instruction_ids)
                ).delete(synchronize_session=False)
            
            db.query(QuestionnaireItem).filter(
                QuestionnaireItem.questionnaire_id == questionnaire_id
            ).delete(synchronize_session=False)
            
            db.delete(questionnaire)
            
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            print(f"Erro ao deletar questionário {questionnaire_id}: {str(e)}")
            raise

        
    def has_responses(self, db: Session, questionnaire_id: int) -> bool:
        questionnaire = db.query(Questionnaire).filter(
            Questionnaire.id == questionnaire_id
        ).first()
        if not questionnaire:
            raise ValueError("Questionário não encontrado")
        
        submission = db.query(QuestionnaireSubmission).filter(
            QuestionnaireSubmission.questionnaire_id == questionnaire_id
        ).first()
        
        return submission is not None

    def update_instruction(self, db: Session, instruction_id: int, instruction_data: InstructionCreate) -> Instruction:
        instruction = db.query(Instruction).filter(Instruction.id == instruction_id).first()
        if not instruction:
            raise ValueError("Instrução não encontrada")
        
        instruction.text = instruction_data.texto
        db.commit()
        db.refresh(instruction)
        return instruction

    def update_questionnaire(self, db: Session, questionnaire_id: int, questionnaire_data: QuestionnaireCreate) -> Questionnaire:    
        questionnaire = db.query(Questionnaire).filter(Questionnaire.id == questionnaire_id).first()
        if not questionnaire:
            raise ValueError("Questionário não encontrado")

        submission = db.query(QuestionnaireSubmission).filter(
            QuestionnaireSubmission.questionnaire_id == questionnaire_id
        ).first()

        if submission is not None:
            raise ValueError("Não é possível editar questionário com respostas")

        questionnaire.title = questionnaire_data.titulo
        questionnaire.description = questionnaire_data.descricao
        questionnaire.question_order = questionnaire_data.question_order
        questionnaire.step_labels = questionnaire_data.step_labels

        db.query(QuestionnaireItem).filter(QuestionnaireItem.questionnaire_id == questionnaire_id).delete()

        for item in questionnaire_data.items:
            db_item = QuestionnaireItem(
                questionnaire_id=questionnaire_id,
                item_type=item.item_type,
                item_id=item.item_id,
                sort_order=item.ordem,
                step=item.step
            )
            db.add(db_item)

        db.commit()
        db.refresh(questionnaire)
        
        return questionnaire
