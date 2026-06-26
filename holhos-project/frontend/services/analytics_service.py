from typing import Any, Dict, List, Optional
from services.api_client import api_client


class AnalyticsService:
    @staticmethod
    def get_dashboard_data(
        questionnaire_id: int,
    ) -> Optional[Dict[str, Any]]:
        return api_client.get(
            f"/analytics/questionnaires/{questionnaire_id}/dashboard-data",
        )

    @staticmethod
    def get_filtered_analytics(
        questionnaire_id: int,
        filters: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        body = filters or {}
        return api_client.post(
            f"/analytics/questionnaires/{questionnaire_id}/filtered-analytics",
            data=body,
        )

    @staticmethod
    def get_chyps_scores(
        questionnaire_id: int,
        filters: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        body = filters or {}
        return api_client.post(
            f"/analytics/questionnaires/{questionnaire_id}/chyps-scores",
            data=body,
        )

    @staticmethod
    def get_crosstab(
        questionnaire_id: int,
        row_variable: str,
        col_variable: str,
        filters: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        body = {
            "row_variable": row_variable,
            "col_variable": col_variable,
        }
        if filters:
            body["filters"] = filters
        return api_client.post(
            f"/analytics/questionnaires/{questionnaire_id}/crosstab",
            data=body,
        )

    @staticmethod
    def get_question_distributions(
        questionnaire_id: int,
    ) -> Optional[Dict[str, Any]]:
        return api_client.get(
            f"/analytics/questionnaires/{questionnaire_id}/question-distributions",
        )

    @staticmethod
    def get_text_responses(
        questionnaire_id: int,
        question_id: int,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
        filters: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        body = {
            "question_id": question_id,
            "search": search,
            "page": page,
            "page_size": page_size,
        }
        if filters:
            body["filters"] = filters
        return api_client.post(
            f"/analytics/questionnaires/{questionnaire_id}/text-responses",
            data=body,
        )

    @staticmethod
    def get_filter_options(
        questionnaire_id: int,
    ) -> Optional[Dict[str, Any]]:
        return api_client.get(
            f"/analytics/questionnaires/{questionnaire_id}/filter-options",
        )

    @staticmethod
    def get_validity_questions(
        questionnaire_id: int,
    ) -> Optional[Dict[str, Any]]:
        return api_client.get(
            f"/analytics/questionnaires/{questionnaire_id}/validity-questions",
        )

    @staticmethod
    def get_crosstab_variables(
        questionnaire_id: int,
    ) -> Optional[Dict[str, Any]]:
        return api_client.get(
            f"/analytics/questionnaires/{questionnaire_id}/crosstab-variables",
        )


analytics_service = AnalyticsService()
