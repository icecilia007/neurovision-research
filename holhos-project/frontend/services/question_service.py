from typing import Dict, Any, Optional
from services.api_client import api_client

class QuestionClient:
    @staticmethod
    def create_question(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            return api_client.post("/questions/", payload)
        except Exception as e:
            raise e

question_client = QuestionClient()
