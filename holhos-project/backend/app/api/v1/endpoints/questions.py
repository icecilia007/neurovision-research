from fastapi import APIRouter, HTTPException
from app.dependencies import QuestionServiceDep, DatabaseDep
from app.schemas.question import QuestionCreate, QuestionResponse, QuestionOptionCreate, QuestionOptionResponse
from typing import List
import sys

router = APIRouter()

@router.post("/", response_model=QuestionResponse)
def create_question(
    question: QuestionCreate,
    db: DatabaseDep,
    question_service: QuestionServiceDep
):
    try:
        db_question = question_service.create_question(db, question)
        return db_question
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{question_id}", response_model=QuestionResponse)
def get_question(
    question_id: int,
    db: DatabaseDep,
    question_service: QuestionServiceDep
):
    try:
        question = question_service.get_question_by_id(db, question_id)
        return question
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/by-caption/{caption}", response_model=QuestionResponse)
def get_question_by_caption(
    caption: str,
    db: DatabaseDep,
    question_service: QuestionServiceDep
):
    try:
        question = question_service.get_question_by_caption(db, caption)
        return question
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{question_id}/options", response_model=QuestionOptionResponse)
def add_option_to_question(
    question_id: int,
    option: QuestionOptionCreate,
    db: DatabaseDep,
    question_service: QuestionServiceDep
):
    try:
        db_option = question_service.add_option_to_question(db, question_id, option)
        return db_option
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/", response_model=List[QuestionResponse])
def list_questions(
    db: DatabaseDep,
    question_service: QuestionServiceDep,
    skip: int = 0,
    limit: int = 100
):
    questions = question_service.list_questions(db, skip, limit)
    return questions

@router.delete("/{question_id}")
def delete_question(
    question_id: int,
    db: DatabaseDep,
    question_service: QuestionServiceDep
):
    try:
        question_service.delete_question(db, question_id)
        return {"message": "Pergunta deletada com sucesso"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/{question_id}", response_model=dict)
def update_question(
    question_id: int,
    question_data: dict,
    db: DatabaseDep,
    question_service: QuestionServiceDep
):
    try:
        updated = question_service.update_question(db, question_id, question_data)
        return {"id": updated.id, "message": "Pergunta atualizada com sucesso"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar: {str(e)}")
