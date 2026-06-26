from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.user_service import UserService
from app.services.question_service import QuestionService
from app.services.questionnaire_service import QuestionnaireService
from app.services.response_service import ResponseService
from app.services.report_service import ReportService
from app.services.analytics_service import AnalyticsService

# Dependency functions
def get_user_service() -> UserService:
    return UserService()

def get_question_service() -> QuestionService:
    return QuestionService()

def get_questionnaire_service() -> QuestionnaireService:
    return QuestionnaireService()

def get_response_service() -> ResponseService:
    return ResponseService()

def get_report_service() -> ReportService:
    return ReportService()

def get_analytics_service() -> AnalyticsService:
    return AnalyticsService()

UserServiceDep = Annotated[UserService, Depends(get_user_service)]
QuestionServiceDep = Annotated[QuestionService, Depends(get_question_service)]
QuestionnaireServiceDep = Annotated[QuestionnaireService, Depends(get_questionnaire_service)]
ResponseServiceDep = Annotated[ResponseService, Depends(get_response_service)]
ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]
AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]
DatabaseDep = Annotated[Session, Depends(get_db)]
