from typing import Dict, Any, Optional
from services.api_client import api_client
import requests
from nicegui import ui
from config import config


class ReportService:
    @staticmethod
    def get_full_report(questionnaire_id: int) -> Optional[Dict[str, Any]]:
        return api_client.get(f"/reports/questionnaires/{questionnaire_id}/full-report")

    @staticmethod
    def get_summary_report(questionnaire_id: int) -> Optional[Dict[str, Any]]:
        return api_client.get(f"/reports/questionnaires/{questionnaire_id}/summary")

    @staticmethod
    def get_analytics(questionnaire_id: int) -> Optional[Dict[str, Any]]:
        return api_client.get(f"/reports/questionnaires/{questionnaire_id}/analytics")

    @staticmethod
    def download_report(questionnaire_id: int, format_type: str = 'csv') -> bool:
        try:
            url = f"{config.api_url}/reports/questionnaires/{questionnaire_id}/export?format={format_type}"
            response = requests.get(url)

            if response.status_code == 200:
                filename = f"questionnaire_{questionnaire_id}_report.{format_type}"
                ui.download(response.content, filename)
                return True
            else:
                return False
        except Exception as e:
            print(f"Erro ao fazer download: {e}")
            return False

    @staticmethod
    def download_csv_report(questionnaire_id: int) -> bool:
        return ReportService.download_report(questionnaire_id, 'csv')

    @staticmethod
    def download_json_report(questionnaire_id: int) -> bool:
        return ReportService.download_report(questionnaire_id, 'json')

    @staticmethod
    def custom_export(
        questionnaire_id: int,
        question_ids: list,
        meta_fields: list,
        date_from: str,
        date_to: str,
        format_type: str,
    ) -> bytes:
        payload = {
            'question_ids': question_ids,
            'meta_fields':  meta_fields,
            'date_from':    date_from or None,
            'date_to':      date_to or None,
            'format':       format_type,
        }
        url = f"{config.api_url}/reports/questionnaires/{questionnaire_id}/custom-export"
        response = requests.post(url, json=payload)
        if response.status_code == 404:
            detail = response.json().get('detail', 'Nenhum dado encontrado')
            raise Exception(detail)
        if response.status_code != 200:
            raise Exception(f'Erro ao exportar: HTTP {response.status_code}')
        return response.content


report_service = ReportService()
