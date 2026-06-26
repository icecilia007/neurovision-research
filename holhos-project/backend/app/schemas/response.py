from pydantic import BaseModel, validator, Field
from typing import List, Optional
from datetime import datetime


class AnswerCreate(BaseModel):
    question_id: int = Field(..., description="ID da pergunta")
    selected_options: Optional[List[int]] = Field(default=[], description="IDs das opções selecionadas")
    text_response: Optional[str] = Field(None, description="Resposta de texto livre")

    @validator('question_id')
    def validate_question_id(cls, v):
        if v <= 0:
            raise ValueError('ID da pergunta deve ser maior que zero')
        return v

    @validator('selected_options')
    def validate_selected_options(cls, v):
        if v is None:
            return []
        valid_options = [opt for opt in v if isinstance(opt, int) and opt > 0]
        return list(set(valid_options))

    @validator('text_response')
    def validate_text_response(cls, v):
        if v is not None and len(v.strip()) == 0:
            return None
        return v


class SubmissionCreate(BaseModel):
    questionnaire_id: int = Field(..., description="ID do questionário")
    answers: List[AnswerCreate] = Field(..., min_items=1,
                                        description="Lista de respostas - TODAS as perguntas devem ser respondidas")

    @validator('questionnaire_id')
    def validate_questionnaire_id(cls, v):
        if v <= 0:
            raise ValueError('ID do questionário deve ser maior que zero')
        return v

    @validator('answers')
    def validate_answers(cls, v):
        if not v or len(v) == 0:
            raise ValueError('Pelo menos uma resposta é obrigatória')

        question_ids = [answer.question_id for answer in v]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError('Não é possível responder a mesma pergunta múltiplas vezes')

        return v

    class Config:
        schema_extra = {
            "example": {
                "questionnaire_id": 1,
                "answers": [
                    {
                        "question_id": 1,
                        "selected_options": [2, 4],
                        "text_response": None
                    },
                    {
                        "question_id": 2,
                        "selected_options": [],
                        "text_response": "Minha resposta detalhada aqui"
                    }
                ]
            }
        }


class AnswerResponse(BaseModel):
    id: int
    question_id: int
    selected_options: Optional[List[int]]
    text_response: Optional[str]
    score: float

    class Config:
        from_attributes = True


class SubmissionResponse(BaseModel):
    id: int
    questionnaire_id: int
    total_score: float
    submitted_at: datetime
    answers: List[AnswerResponse]

    class Config:
        from_attributes = True


class SubmissionValidationResponse(BaseModel):
    is_valid: bool
    message: str
    total_questions: int
    answered_questions: int
    missing_questions: List[int] = []
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None