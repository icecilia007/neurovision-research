from typing import Dict, Any, Optional, List
from services.api_client import api_client


class UserService:
    @staticmethod
    def create_user(user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return api_client.post("/users/", user_data)

    @staticmethod
    def get_user(user_id: int) -> Optional[Dict[str, Any]]:
        return api_client.get(f"/users/{user_id}")

    @staticmethod
    def list_users() -> Optional[List[Dict[str, Any]]]:
        return api_client.get("/users/")

    @staticmethod
    def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
        login_data = {
            "email": email,
            "senha": password
        }
        response = api_client.post("/users/login", login_data)

        if response and response.get('success'):
            user_id = response.get('user_id')
            if user_id:
                user_data = UserService.get_user(user_id)
                if user_data:
                    return user_data

            return {
                'id': response.get('user_id'),
                'nome_completo': response.get('nome_completo'),
                'email': email
            }

        return None

    @staticmethod
    def login_user(email: str, password: str) -> Optional[Dict[str, Any]]:
        login_data = {
            "email": email,
            "senha": password
        }

        return api_client.post("/users/login", login_data)


user_service = UserService()
