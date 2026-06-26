import requests
from typing import Dict, Any, Optional
from config import config

class APIClient:
    def __init__(self):
        self.base_url = config.api_url
        self.session = requests.Session()

    @staticmethod
    def _safe_user_message(status_code: int, default_msg: str) -> str:
        if status_code == 404:
            return 'Questionário não encontrado'
        if status_code >= 500:
            return 'Não foi possível processar sua solicitação agora. Tente novamente.'
        return default_msg

    def post(self, endpoint: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            response = self.session.post(f"{self.base_url}{endpoint}", json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            try:
                error_data = e.response.json()
                error_msg = (
                    error_data.get('detail')
                    or error_data.get('message')
                    or error_data.get('error_details')
                    or str(e)
                )
            except Exception:
                error_msg = str(e)

            print(f"Erro backend POST {endpoint}: status={e.response.status_code} detail={error_msg}")
            raise Exception(self._safe_user_message(e.response.status_code, 'Não foi possível concluir a operação')) from e
        except requests.RequestException as e:
            print(f"Erro na requisição POST: {e}")
            raise Exception('Não foi possível concluir a operação') from e


    def get(self, endpoint: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.session.get(f"{self.base_url}{endpoint}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            try:
                error_data = e.response.json()
                error_msg = (
                    error_data.get('detail')
                    or error_data.get('message')
                    or error_data.get('error_details')
                    or str(e)
                )
            except Exception:
                error_msg = str(e)

            print(f"Erro backend GET {endpoint}: status={e.response.status_code} detail={error_msg}")
            raise Exception(self._safe_user_message(e.response.status_code, 'Não foi possível carregar os dados')) from e
        except requests.RequestException as e:
            print(f"Erro na requisição GET: {e}")
            raise Exception('Não foi possível carregar os dados') from e

    def delete(self, endpoint: str) -> bool:
        try:
            response = self.session.delete(f"{self.base_url}{endpoint}")
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"Erro na requisição DELETE: {e}")
            return False
        
    def put(self, endpoint: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            response = self.session.put(f"{self.base_url}{endpoint}", json=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Erro na requisição PUT: {e}")
            return None

api_client = APIClient()
