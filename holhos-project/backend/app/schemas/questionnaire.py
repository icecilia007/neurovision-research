from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from typing import List, Optional, Union
from app.models.questionnaire import QuestionOrderEnum, ItemTypeEnum
from .question import QuestionForResponse
from .instruction import InstructionResponse
from datetime import datetime

class QuestionnaireItemCreate(BaseModel):
    item_type: ItemTypeEnum
    item_id: int
    ordem: int
    step: int = 1

class QuestionnaireCreate(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    question_order: QuestionOrderEnum = QuestionOrderEnum.custom
    step_labels: Optional[List[str]] = None
    items: List[QuestionnaireItemCreate]
    criador_id: int

class QuestionnaireResponse(BaseModel):
    id: int
    titulo: str = Field(validation_alias=AliasChoices('titulo', 'title'))
    descricao: Optional[str] = Field(default=None, validation_alias=AliasChoices('descricao', 'description'))
    question_order: QuestionOrderEnum
    ativo: bool = Field(validation_alias=AliasChoices('ativo', 'is_active'))
    criador_id: int = Field(validation_alias=AliasChoices('criador_id', 'creator_id'))
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class QuestionnaireItemForResponse(BaseModel):
    tipo: ItemTypeEnum
    ordem: int = Field(validation_alias=AliasChoices('ordem', 'sort_order'))
    step: int = 1
    content: Union[QuestionForResponse, InstructionResponse]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class QuestionnaireForResponse(BaseModel):
    id: int
    titulo: str = Field(validation_alias=AliasChoices('titulo', 'title'))
    descricao: Optional[str] = Field(default=None, validation_alias=AliasChoices('descricao', 'description'))
    question_order: str
    step_labels: Optional[List[str]] = None
    items: List[QuestionnaireItemForResponse]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class GenerateLinkResponse(BaseModel):
    questionnaire_id: int
    link: str
