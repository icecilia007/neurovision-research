from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from typing import List, Optional
from app.models.question import QuestionTypeEnum

class QuestionOptionCreate(BaseModel):
    texto: str
    ordem: int
    is_correct: bool = False
    peso: float = 0.0

class QuestionOptionResponse(BaseModel):
    id: int
    texto: str = Field(validation_alias=AliasChoices('texto', 'text'))
    ordem: int = Field(validation_alias=AliasChoices('ordem', 'sort_order'))
    is_correct: bool
    peso: float = Field(validation_alias=AliasChoices('peso', 'weight'))

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class QuestionCreate(BaseModel):
    caption: Optional[str] = None
    titulo: Optional[str] = None
    texto: str
    tipo: QuestionTypeEnum
    obrigatoria: bool = True
    peso: float = 1.0
    depends_on_question_id: Optional[int] = None
    depends_on_option_id: Optional[int] = None
    options: Optional[List[QuestionOptionCreate]] = []

class QuestionResponse(BaseModel):
    id: int
    caption: Optional[str] = None
    titulo: Optional[str] = Field(default=None, validation_alias=AliasChoices('titulo', 'title'))
    texto: str = Field(validation_alias=AliasChoices('texto', 'text'))
    tipo: QuestionTypeEnum = Field(validation_alias=AliasChoices('tipo', 'question_type'))
    obrigatoria: bool = Field(default=True, validation_alias=AliasChoices('obrigatoria', 'is_required'))
    peso: float = Field(validation_alias=AliasChoices('peso', 'weight'))
    depends_on_question_id: Optional[int] = None
    depends_on_option_id: Optional[int] = None
    options: List[QuestionOptionResponse]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class QuestionForResponse(BaseModel):
    id: int
    caption: Optional[str] = None
    titulo: Optional[str] = Field(default=None, validation_alias=AliasChoices('titulo', 'title'))
    texto: str = Field(validation_alias=AliasChoices('texto', 'text'))
    tipo: QuestionTypeEnum = Field(validation_alias=AliasChoices('tipo', 'question_type'))
    obrigatoria: bool = Field(default=True, validation_alias=AliasChoices('obrigatoria', 'is_required'))
    peso: float = Field(validation_alias=AliasChoices('peso', 'weight'))
    depends_on_question_id: Optional[int] = None
    depends_on_option_id: Optional[int] = None
    options: List[QuestionOptionResponse]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
