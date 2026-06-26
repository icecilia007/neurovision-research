from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, Enum, Float, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class QuestionTypeEnum(str, enum.Enum):
    single = "single"
    multiple = "multiple"
    free_text = "free_text"

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    caption = Column(String(100), nullable=True, unique=True, index=True)
    title = Column(String(255), nullable=True)
    text = Column(Text, nullable=False)
    question_type = Column(Enum(QuestionTypeEnum), nullable=False)
    is_required = Column(Boolean, nullable=False, default=True, server_default='true')
    weight = Column(Float, default=1.0)
    depends_on_question_id = Column(Integer, ForeignKey("questions.id"), nullable=True)
    depends_on_option_id = Column(Integer, ForeignKey("question_options.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # depends_on_option_id adds a second FK path between questions and
    # question_options, so both sides must name their join column explicitly.
    options = relationship(
        "QuestionOption",
        back_populates="question",
        cascade="all, delete-orphan",
        foreign_keys="QuestionOption.question_id",
    )
    answers = relationship("Answer", back_populates="question")

class QuestionOption(Base):
    __tablename__ = "question_options"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    text = Column(Text, nullable=False)
    sort_order = Column(Integer, nullable=False)
    is_correct = Column(Boolean, default=False)
    weight = Column(Float, default=0.0)

    question = relationship("Question", back_populates="options", foreign_keys=[question_id])
