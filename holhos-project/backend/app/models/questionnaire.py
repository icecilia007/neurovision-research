from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, Enum, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class QuestionOrderEnum(str, enum.Enum):
    custom = "custom"
    ascending = "ascending"
    descending = "descending"
    random = "random"


class ItemTypeEnum(str, enum.Enum):
    question = "question"
    instruction = "instruction"
    term = "term"


class Questionnaire(Base):
    __tablename__ = "questionnaires"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    question_order = Column(Enum(QuestionOrderEnum), default=QuestionOrderEnum.custom)
    step_labels = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    creator = relationship("User", backref="created_questionnaires")
    items = relationship("QuestionnaireItem", back_populates="questionnaire", cascade="all, delete-orphan")
    submissions = relationship("QuestionnaireSubmission", back_populates="questionnaire")


class QuestionnaireItem(Base):
    __tablename__ = "questionnaire_items"

    id = Column(Integer, primary_key=True, index=True)
    questionnaire_id = Column(Integer, ForeignKey("questionnaires.id"), nullable=False)
    item_type = Column(Enum(ItemTypeEnum), nullable=False)
    item_id = Column(Integer, nullable=False)
    sort_order = Column(Integer, nullable=False)
    step = Column(Integer, nullable=False, default=1, server_default='1')

    questionnaire = relationship("Questionnaire", back_populates="items")
