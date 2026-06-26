from typing import Dict, Any, Optional
from services.api_client import api_client

class InstructionClient:
    @staticmethod
    def create_instruction(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return api_client.post("/questionnaires/instructions", payload)

instruction_client = InstructionClient()
