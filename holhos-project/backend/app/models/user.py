from sqlalchemy import Column, Integer, String, Enum, Date  
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class GenderEnum(str, enum.Enum):
    masculino = "masculino"
    feminino = "feminino"
    outro = "outro"
    nao_informar = "nao_informar"

class EducationLevelEnum(str, enum.Enum):
    fundamental_incompleto = "fundamental_incompleto"
    fundamental_completo = "fundamental_completo"
    medio_incompleto = "medio_incompleto"
    medio_completo = "medio_completo"
    superior_incompleto = "superior_incompleto"
    superior_completo = "superior_completo"
    pos_graduacao = "pos_graduacao"
    mestrado = "mestrado"
    doutorado = "doutorado"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    gender = Column(Enum(GenderEnum), nullable=False)
    birth_date = Column(Date, nullable=False)
    education_level = Column(Enum(EducationLevelEnum, name='escolaridadeenum'), nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
