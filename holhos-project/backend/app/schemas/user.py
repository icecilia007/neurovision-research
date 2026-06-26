from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date  # ← Adicionar
from app.models.user import GenderEnum, EducationLevelEnum

class UserCreate(BaseModel):
    nome_completo: str
    genero: GenderEnum
    nascimento: date
    escolaridade: EducationLevelEnum
    email: EmailStr
    telefone: str
    senha: str

class UserUpdate(BaseModel):
    nome_completo: Optional[str] = None
    genero: Optional[GenderEnum] = None
    nascimento: Optional[date] = None
    escolaridade: Optional[EducationLevelEnum] = None
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    nome_completo: str = Field(validation_alias='full_name')
    genero: GenderEnum = Field(validation_alias='gender')
    nascimento: date = Field(validation_alias='birth_date')
    escolaridade: EducationLevelEnum = Field(validation_alias='education_level')
    email: str
    telefone: str = Field(validation_alias='phone')

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email: EmailStr
    senha: str

class LoginResponse(BaseModel):
    success: bool
    message: str
    user_id: Optional[int] = None
    nome_completo: Optional[str] = None
