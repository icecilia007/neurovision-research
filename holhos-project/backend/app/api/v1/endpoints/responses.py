from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from app.dependencies import ResponseServiceDep, DatabaseDep
from app.schemas.response import SubmissionCreate, SubmissionResponse
from typing import List, Optional

router = APIRouter()


@router.post("/submit")
def submit_questionnaire_response(
        submission: SubmissionCreate,
        db: DatabaseDep,
        response_service: ResponseServiceDep
):
    """
    Submete uma resposta de questionário com validação integrada
    Retorna erros estruturados para o frontend
    """
    try:
        validation = response_service.validate_submission(db, submission)

        if not validation.is_valid:
            first_error = validation.errors[0] if validation.errors else None
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": first_error or validation.message,
                    "summary_message": validation.message,
                    "validation_details": {
                        "total_questions": validation.total_questions,
                        "answered_questions": validation.answered_questions,
                        "missing_questions": validation.missing_questions,
                        "completion_percentage": round(
                            (validation.answered_questions / validation.total_questions * 100),
                            1) if validation.total_questions > 0 else 0.0
                    },
                    "errors": validation.errors,
                    "warnings": validation.warnings,
                    "error_type": "validation_failed"
                }
            )

        db_submission = response_service.submit_questionnaire_response(db, submission)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Resposta enviada com sucesso! 🎉",
                "data": {
                    "id": db_submission.id,
                    "questionnaire_id": db_submission.questionnaire_id,
                    "total_score": db_submission.total_score,
                    "submitted_at": db_submission.submitted_at.isoformat(),
                    "answers_count": len(db_submission.answers)
                }
            }
        )

    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "Erro na validação da submissão",
                "error_details": str(e),
                "error_type": "service_validation_error"
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Erro interno do servidor",
                "error_details": str(e),
                "error_type": "internal_error"
            }
        )


@router.get("/submissions/{submission_id}", response_model=SubmissionResponse)
def get_submission(
        submission_id: int,
        db: DatabaseDep,
        response_service: ResponseServiceDep
):
    """
    Busca uma submissão específica por ID
    """
    try:
        submission = response_service.get_submission_by_id(db, submission_id)
        return submission
    except ValueError as e:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": "Submissão não encontrada",
                "error_details": str(e),
                "error_type": "not_found"
            }
        )


@router.get("/questionnaires/{questionnaire_id}/submissions", response_model=List[SubmissionResponse])
def list_questionnaire_submissions(
        questionnaire_id: int,
        db: DatabaseDep,
        response_service: ResponseServiceDep,
        limit: int = Query(default=100, le=1000),
        skip: int = Query(default=0, ge=0)
):
    """
    Lista submissões de um questionário específico com paginação
    """
    try:
        submissions = response_service.list_submissions_by_questionnaire(db, questionnaire_id)
        paginated_submissions = submissions[skip:skip + limit]
        return paginated_submissions
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Erro ao buscar submissões",
                "error_details": str(e),
                "error_type": "internal_error"
            }
        )


@router.get("/questionnaires/{questionnaire_id}/statistics")
def get_submission_statistics(
        questionnaire_id: int,
        db: DatabaseDep,
        response_service: ResponseServiceDep
):
    """
    Retorna estatísticas das submissões de um questionário
    """
    try:
        statistics = response_service.get_submission_statistics(db, questionnaire_id)
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": statistics
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Erro ao calcular estatísticas",
                "error_details": str(e),
                "error_type": "internal_error"
            }
        )


@router.delete("/submissions/{submission_id}")
def delete_submission(
        submission_id: int,
        db: DatabaseDep,
        response_service: ResponseServiceDep
):
    """
    Remove uma submissão e suas respostas associadas
    """
    try:
        response_service.delete_submission(db, submission_id)
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Submissão deletada com sucesso"
            }
        )
    except ValueError as e:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": "Submissão não encontrada",
                "error_details": str(e),
                "error_type": "not_found"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Erro ao deletar submissão",
                "error_details": str(e),
                "error_type": "internal_error"
            }
        )
