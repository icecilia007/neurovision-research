from typing import Dict, Any, Optional
from services.api_client import api_client


class ResponseService:

    @staticmethod
    def submit_response(submission_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return api_client.post("/responses/submit", submission_data)

    @staticmethod
    def get_submission(submission_id: int) -> Optional[Dict[str, Any]]:
        return api_client.get(f"/responses/submissions/{submission_id}")


response_service = ResponseService()
