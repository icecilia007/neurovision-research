from sqlalchemy import Column, Integer, ForeignKey, Float, DateTime, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class QuestionnaireSubmission(Base):
    __tablename__ = "questionnaire_submissions"

    id = Column(Integer, primary_key=True, index=True)
    questionnaire_id = Column(Integer, ForeignKey("questionnaires.id"), nullable=False)
    total_score = Column(Float, default=0.0)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())

    questionnaire = relationship("Questionnaire", back_populates="submissions")
    answers = relationship("Answer", back_populates="submission", cascade="all, delete-orphan")

class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("questionnaire_submissions.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    selected_options = Column(JSON)
    text_response = Column(Text)
    score = Column(Float, default=0.0)

    submission = relationship("QuestionnaireSubmission", back_populates="answers")
    question = relationship("Question", back_populates="answers")
