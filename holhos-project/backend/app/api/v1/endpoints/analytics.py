from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.dependencies import AnalyticsServiceDep, DatabaseDep, ReportServiceDep
from app.schemas.analytics import CrosstabRequest, FilterParams, TextResponseQuery
from app.services.chyps_config import CHYPS_V_SCALE_ITEMS, DEMOGRAPHIC_FILTERS
from app.models import Question, QuestionOption, QuestionnaireItem

router = APIRouter()


@router.post("/questionnaires/{questionnaire_id}/chyps-scores")
def get_chyps_scores(
    questionnaire_id: int,
    filters: Optional[FilterParams] = None,
    db: DatabaseDep = ...,
    report_service: ReportServiceDep = ...,
    analytics_service: AnalyticsServiceDep = ...,
):
    try:
        report_data = report_service.get_full_report(db, questionnaire_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    submissions = report_data["anonymous_submissions"]
    filter_dict = filters.to_filter_dict() if filters else {}
    if filter_dict:
        submissions = analytics_service.filter_submissions(submissions, filter_dict)

    caption_to_options = _build_caption_option_map(db, questionnaire_id)

    scores = analytics_service.compute_chyps_v_scores(submissions, caption_to_options)

    return {
        "global_stats": scores["global_stats"],
        "subscale_stats": scores["subscale_stats"],
        "cronbachs_alpha": scores["cronbachs_alpha"],
        "respondent_count": scores["global_stats"]["n"],
        "filtered": bool(filter_dict),
        "respondent_scores": scores.get("respondent_scores", []),
        "spearman_correlation": scores.get("spearman_correlation"),
    }


@router.post("/questionnaires/{questionnaire_id}/crosstab")
def get_crosstab(
    questionnaire_id: int,
    request: CrosstabRequest,
    db: DatabaseDep = ...,
    report_service: ReportServiceDep = ...,
    analytics_service: AnalyticsServiceDep = ...,
):
    try:
        report_data = report_service.get_full_report(db, questionnaire_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    submissions = report_data["anonymous_submissions"]
    if request.filters:
        submissions = analytics_service.filter_submissions(
            submissions, request.filters.to_filter_dict()
        )

    row_values = _extract_variable_values(submissions, request.row_variable)
    col_values = _extract_variable_values(submissions, request.col_variable)

    result = analytics_service.compute_crosstab(row_values, col_values)

    return {
        "row_variable": request.row_variable,
        "col_variable": request.col_variable,
        **result,
    }


@router.get("/questionnaires/{questionnaire_id}/question-distributions")
def get_question_distributions(
    questionnaire_id: int,
    db: DatabaseDep = ...,
    report_service: ReportServiceDep = ...,
    analytics_service: AnalyticsServiceDep = ...,
):
    try:
        report_data = report_service.get_full_report(db, questionnaire_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    question_stats = report_data["question_statistics"]
    distributions = analytics_service.compute_question_distributions(question_stats)

    return {"distributions": distributions}


@router.post("/questionnaires/{questionnaire_id}/text-responses")
def get_text_responses(
    questionnaire_id: int,
    query: TextResponseQuery,
    db: DatabaseDep = ...,
    report_service: ReportServiceDep = ...,
    analytics_service: AnalyticsServiceDep = ...,
):
    try:
        report_data = report_service.get_full_report(db, questionnaire_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    submissions = report_data["anonymous_submissions"]
    if query.filters:
        submissions = analytics_service.filter_submissions(
            submissions, query.filters.to_filter_dict()
        )

    responses = []
    for sub in submissions:
        for ans in sub.get("answers", []):
            if ans.get("question_id") == query.question_id and ans.get("text_response"):
                text = ans["text_response"]
                if query.search and query.search.lower() not in text.lower():
                    continue
                responses.append({
                    "submission_id": sub["submission_id"],
                    "text": text,
                    "submitted_at": sub["submitted_at"],
                })

    total = len(responses)
    page = query.page
    page_size = query.page_size
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total else 0,
        "responses": responses[start:end],
    }


@router.get("/questionnaires/{questionnaire_id}/filter-options")
def get_filter_options(
    questionnaire_id: int,
    db: DatabaseDep = ...,
    report_service: ReportServiceDep = ...,
):
    try:
        report_data = report_service.get_full_report(db, questionnaire_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    submissions = report_data["anonymous_submissions"]
    options: dict = {}

    for demo_key, config in DEMOGRAPHIC_FILTERS.items():
        pattern = config["pattern"].lower()
        values = set()
        for sub in submissions:
            for ans in sub.get("answers", []):
                ans_text = (ans.get("question_text") or "").lower()
                if pattern not in ans_text:
                    continue
                texts = ans.get("selected_option_texts", [])
                if not texts and ans.get("text_response"):
                    texts = [ans["text_response"]]
                for t in texts:
                    if t:
                        values.add(t)
        if values:
            options[demo_key] = sorted(v for v in values if v)

    return {"filter_options": options}


@router.get("/questionnaires/{questionnaire_id}/dashboard-data")
def get_dashboard_data(
    questionnaire_id: int,
    db: DatabaseDep = ...,
    report_service: ReportServiceDep = ...,
    analytics_service: AnalyticsServiceDep = ...,
):
    try:
        report_data = report_service.get_full_report(db, questionnaire_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    submissions = report_data["anonymous_submissions"]
    caption_to_options = _build_caption_option_map(db, questionnaire_id)
    scores = analytics_service.compute_chyps_v_scores(submissions, caption_to_options)

    question_stats = report_data["question_statistics"]
    distributions = analytics_service.compute_question_distributions(question_stats)

    filter_options = _compute_filter_options(submissions)

    crosstab_vars = _get_crosstab_variables(db, questionnaire_id)

    return {
        "questionnaire": report_data["questionnaire"],
        "general_stats": report_data["general_stats"],
        "anonymous_submissions": report_data["anonymous_submissions"],
        "analytics": {
            "global_stats": scores["global_stats"],
            "subscale_stats": scores["subscale_stats"],
            "cronbachs_alpha": scores["cronbachs_alpha"],
            "respondent_scores": scores.get("respondent_scores", []),
            "spearman_correlation": scores.get("spearman_correlation"),
        },
        "distributions": distributions,
        "filter_options": filter_options,
        "crosstab_variables": crosstab_vars,
    }


@router.post("/questionnaires/{questionnaire_id}/filtered-analytics")
def get_filtered_analytics(
    questionnaire_id: int,
    filters: Optional[FilterParams] = None,
    db: DatabaseDep = ...,
    report_service: ReportServiceDep = ...,
    analytics_service: AnalyticsServiceDep = ...,
):
    try:
        report_data = report_service.get_full_report(db, questionnaire_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    submissions = report_data["anonymous_submissions"]
    filter_dict = filters.to_filter_dict() if filters else {}
    if filter_dict:
        submissions = analytics_service.filter_submissions(submissions, filter_dict)

    caption_to_options = _build_caption_option_map(db, questionnaire_id)
    scores = analytics_service.compute_chyps_v_scores(submissions, caption_to_options)

    return {
        "global_stats": scores["global_stats"],
        "subscale_stats": scores["subscale_stats"],
        "cronbachs_alpha": scores["cronbachs_alpha"],
        "respondent_scores": scores.get("respondent_scores", []),
        "spearman_correlation": scores.get("spearman_correlation"),
    }


@router.get("/questionnaires/{questionnaire_id}/validity-questions")
def get_validity_questions(
    questionnaire_id: int,
    db: DatabaseDep,
):
    """Returns all single/multiple-choice questions in the questionnaire with their options.
    Used by the frontend to build the validity (attention-check) filter."""
    items = db.query(QuestionnaireItem).filter(
        QuestionnaireItem.questionnaire_id == questionnaire_id,
        QuestionnaireItem.item_type.in_(["question", "term"]),
    ).order_by(QuestionnaireItem.sort_order).all()

    questions = []
    for item in items:
        question = db.query(Question).filter(Question.id == item.item_id).first()
        if not question or question.question_type not in ("single", "multiple"):
            continue
        opts = db.query(QuestionOption).filter(
            QuestionOption.question_id == question.id
        ).order_by(QuestionOption.sort_order).all()
        questions.append({
            "caption": question.caption or f"q{question.id}",
            "text": question.title or question.text or "",
            "options": [
                {"id": o.id, "text": o.text, "sort_order": o.sort_order}
                for o in opts
            ],
        })

    return {"questions": questions}


@router.get("/questionnaires/{questionnaire_id}/crosstab-variables")
def get_crosstab_variables(
    questionnaire_id: int,
    db: DatabaseDep = ...,
):
    items = db.query(QuestionnaireItem).filter(
        QuestionnaireItem.questionnaire_id == questionnaire_id,
        QuestionnaireItem.item_type.in_(["question", "term"]),
    ).order_by(QuestionnaireItem.sort_order).all()

    variables = []
    for item in items:
        question = db.query(Question).filter(Question.id == item.item_id).first()
        if not question:
            continue
        variables.append({
            "caption": question.caption or f"q{question.id}",
            "text": question.title or question.text,
            "type": question.question_type,
        })

    return {"variables": variables}


# ── Helpers ────────────────────────────────────────────────────────────

def _build_caption_option_map(db, questionnaire_id: int) -> dict:
    items = db.query(QuestionnaireItem).filter(
        QuestionnaireItem.questionnaire_id == questionnaire_id,
        QuestionnaireItem.item_type.in_(["question", "term"]),
    ).all()

    caption_map = {}
    for item in items:
        question = db.query(Question).filter(Question.id == item.item_id).first()
        if not question or not question.caption:
            continue
        opts = db.query(QuestionOption).filter(
            QuestionOption.question_id == question.id
        ).all()
        caption_map[question.caption] = [
            {"id": o.id, "text": o.text, "weight": o.weight, "sort_order": o.sort_order}
            for o in opts
        ]
    return caption_map


def _extract_variable_values(submissions: list, variable: str) -> list:
    values = []
    for sub in submissions:
        found = None
        for ans in sub.get("answers", []):
            if ans.get("caption") == variable or str(ans.get("question_id")) == variable:
                if ans.get("selected_option_texts"):
                    found = ans["selected_option_texts"][0]
                elif ans.get("text_response"):
                    found = ans["text_response"]
                elif ans.get("score") is not None:
                    found = ans["score"]
                break
        values.append(found)
    return values


def _compute_filter_options(submissions: list) -> dict:
    options: dict = {}
    for demo_key, config in DEMOGRAPHIC_FILTERS.items():
        pattern = config["pattern"].lower()
        values = set()
        for sub in submissions:
            for ans in sub.get("answers", []):
                ans_text = (ans.get("question_text") or "").lower()
                if pattern not in ans_text:
                    continue
                texts = ans.get("selected_option_texts", [])
                if not texts and ans.get("text_response"):
                    texts = [ans["text_response"]]
                for t in texts:
                    if t:
                        values.add(t)
        if values:
            if demo_key == "birth_year":
                year_values = []
                for v in values:
                    try:
                        parts = str(v).strip().split("/")
                        if len(parts) == 3:
                            year_values.append(int(parts[2]))
                        else:
                            year_values.append(int(float(v)))
                    except (ValueError, IndexError):
                        pass
                if year_values:
                    options[demo_key] = sorted(year_values)
            else:
                options[demo_key] = sorted(v for v in values if v)
    return options


def _get_crosstab_variables(db, questionnaire_id: int) -> list:
    items = db.query(QuestionnaireItem).filter(
        QuestionnaireItem.questionnaire_id == questionnaire_id,
        QuestionnaireItem.item_type.in_(["question", "term"]),
    ).order_by(QuestionnaireItem.sort_order).all()

    variables = []
    for item in items:
        question = db.query(Question).filter(Question.id == item.item_id).first()
        if not question:
            continue
        variables.append({
            "caption": question.caption or f"q{question.id}",
            "text": question.title or question.text,
            "type": question.question_type,
        })
    return variables
