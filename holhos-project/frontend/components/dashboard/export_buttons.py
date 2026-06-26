from nicegui import ui
from services.report_service import report_service


class ExportButtons:
    def __init__(self, questionnaire_id: int):
        self.questionnaire_id = questionnaire_id

    def render(self, container=None):
        target = container or ui.row()
        with target:
            with ui.row().style("gap: 0.75rem; justify-content: center; padding: 1rem 0;"):
                ui.button(
                    "Exportar CSV",
                    on_click=self._export_csv,
                    icon="file_download",
                ).props("outline color=green").style("height: 38px;")

                ui.button(
                    "Exportar Excel",
                    on_click=self._export_excel,
                    icon="table_view",
                ).props("outline color=blue").style("height: 38px;")

    def _export_csv(self):
        try:
            success = report_service.download_report(self.questionnaire_id, "csv")
            if success:
                ui.notify("Download CSV iniciado!", type="positive")
            else:
                ui.notify("Erro ao exportar CSV.", type="negative")
        except Exception as e:
            ui.notify(f"Erro: {e}", type="negative")

    def _export_excel(self):
        try:
            success = report_service.download_report(self.questionnaire_id, "json")
            if success:
                ui.notify("Download JSON iniciado!", type="positive")
            else:
                ui.notify("Erro ao exportar.", type="negative")
        except Exception as e:
            ui.notify(f"Erro: {e}", type="negative")
