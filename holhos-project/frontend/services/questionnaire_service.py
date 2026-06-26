from typing import Dict, Any, Optional
from services.api_client import api_client

class QuestionnaireService:

    @staticmethod
    def create_questionnaire(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return api_client.post("/questionnaires/", payload)

    @staticmethod
    def generate_link(questionnaire_id: int) -> Optional[Dict[str, Any]]:
        return api_client.post(f"/questionnaires/{questionnaire_id}/generate-link", {})

    @staticmethod
    def list_by_creator(criador_id: int):
        return api_client.get(f"/questionnaires/?criador_id={criador_id}")

    @staticmethod
    def delete(questionnaire_id: int) -> bool:
        response = api_client.delete(f"/questionnaires/{questionnaire_id}")
        return response is not None

    @staticmethod
    def get_questionnaire_for_response(questionnaire_id: str) -> Optional[Dict[str, Any]]:
        return api_client.get(f"/questionnaires/{questionnaire_id}/respond")

    @staticmethod
    def check_eligibility(questionnaire_id: int) -> Optional[Dict[str, Any]]:
        return api_client.get(f"/questionnaires/{questionnaire_id}/eligibility")

    @staticmethod
    def update_questionnaire(questionnaire_id: int, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return api_client.put(f"/questionnaires/{questionnaire_id}", payload)


questionnaire_service = QuestionnaireService()
