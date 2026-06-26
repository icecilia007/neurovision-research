from fastapi import APIRouter, HTTPException
import logging
from app.dependencies import QuestionnaireServiceDep, DatabaseDep
from app.schemas.questionnaire import (
    QuestionnaireCreate, QuestionnaireResponse,
    GenerateLinkResponse, QuestionnaireForResponse
)
from app.schemas.instruction import InstructionCreate, InstructionResponse
from typing import List, Optional

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/instructions", response_model=InstructionResponse)
def create_instruction(
    instruction: InstructionCreate,
    db: DatabaseDep,
    questionnaire_service: QuestionnaireServiceDep
):
    try:
        db_instruction = questionnaire_service.create_instruction(db, instruction)
        return db_instruction
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/", response_model=QuestionnaireResponse)
def create_questionnaire(
    questionnaire: QuestionnaireCreate,
    db: DatabaseDep,
    questionnaire_service: QuestionnaireServiceDep
):
    try:
        db_questionnaire = questionnaire_service.create_questionnaire(db, questionnaire)
        return db_questionnaire
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{questionnaire_id}/generate-link", response_model=GenerateLinkResponse)
def generate_questionnaire_link(
    questionnaire_id: int,
    db: DatabaseDep,
    questionnaire_service: QuestionnaireServiceDep
):
    try:
        link_response = questionnaire_service.generate_questionnaire_link(db, questionnaire_id)
        return link_response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{questionnaire_id}/respond", response_model=QuestionnaireForResponse)
def get_questionnaire_for_response(
    questionnaire_id: str,
    db: DatabaseDep,
    questionnaire_service: QuestionnaireServiceDep
):
    try:
        questionnaire_response = questionnaire_service.get_questionnaire_for_response(db, questionnaire_id)
        return questionnaire_response
    except ValueError as e:
        detail = str(e)
        if "Questionário não encontrado" in detail or "ID do questionário inválido" in detail:
            raise HTTPException(status_code=404, detail="Questionário não encontrado")
        logger.exception("Erro de validação ao carregar questionário para resposta")
        raise HTTPException(status_code=500, detail="Não foi possível carregar o questionário no momento")
    except Exception:
        logger.exception("Erro inesperado ao carregar questionário para resposta")
        raise HTTPException(status_code=500, detail="Não foi possível carregar o questionário no momento")


@router.get("/", response_model=List[QuestionnaireResponse])
def list_questionnaires(
    db: DatabaseDep,
    questionnaire_service: QuestionnaireServiceDep,
    skip: int = 0,
    limit: int = 100,
    criador_id: Optional[int] = None
):
    if criador_id is not None:
        questionnaires = questionnaire_service.list_questionnaires_by_creator(db, criador_id)
        return questionnaires
    else:
        questionnaires = questionnaire_service.list_questionnaires(db, skip, limit)
        return questionnaires

@router.get("/{questionnaire_id}", response_model=QuestionnaireResponse)
def get_questionnaire(
    questionnaire_id: int,
    db: DatabaseDep,
    questionnaire_service: QuestionnaireServiceDep
):
    try:
        questionnaire = questionnaire_service.get_questionnaire_by_id(db, questionnaire_id)
        return questionnaire
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{questionnaire_id}", response_model=dict)
def delete_questionnaire(
    questionnaire_id: int,
    db: DatabaseDep,
    questionnaire_service: QuestionnaireServiceDep
):
    try:
        success = questionnaire_service.delete_questionnaire(db, questionnaire_id)
        return {"deleted": success}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{questionnaire_id}/eligibility", response_model=dict)
def check_questionnaire_eligibility(
    questionnaire_id: int,
    db: DatabaseDep,
    questionnaire_service: QuestionnaireServiceDep
):
    try:
        has_responses = questionnaire_service.has_responses(db, questionnaire_id)
        return {"eligible": not has_responses}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/{questionnaire_id}", response_model=QuestionnaireResponse)
def update_questionnaire(
    questionnaire_id: int,
    questionnaire: QuestionnaireCreate,
    db: DatabaseDep,
    questionnaire_service: QuestionnaireServiceDep
):
    try:
        updated = questionnaire_service.update_questionnaire(db, questionnaire_id, questionnaire)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.put("/instructions/{instruction_id}", response_model=InstructionResponse)
def update_instruction(
    instruction_id: int,
    instruction: InstructionCreate,
    db: DatabaseDep,
    questionnaire_service: QuestionnaireServiceDep
):
    try:
        updated = questionnaire_service.update_instruction(db, instruction_id, instruction)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
