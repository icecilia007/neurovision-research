from nicegui import ui
from services.questionnaire_service import questionnaire_service
from services.report_service import report_service
from utils.session_manager import session_manager
import router
from pages.report_detailed import QuestionnaireDetailedReport
from pages.report_analytics import QuestionnaireAnalyticsReport
from pages.custom_export_page import CustomExportPage







class ReportsPage:
    def __init__(self, on_back=None, content_container=None):
        self.on_back = on_back
        self.content_container = content_container
        self.grid_container = None







    def render(self):
        if not hasattr(ReportsPage, '_css_injected'):
            ui.add_head_html('''
            <style>
                /* Desktop: Altura FIXA + Scroll interno + Largura mínima */
                @media (min-width: 769px) {
                    .report-card-wrapper {
                        height: 330px !important;
                        min-width: 380px !important;  /* ✅ Largura mínima no desktop */
                        display: flex !important;
                        flex-direction: column !important;
                    }
                    
                    .report-card-content {
                        flex: 1 !important;
                        overflow-y: auto !important;
                        overflow-x: hidden !important;
                        padding-right: 8px !important;
                    }
                    
                    .report-card-buttons {
                        margin-top: 12px !important;
                        padding-top: 12px !important;
                        border-top: 1px solid rgba(0,0,0,0.08) !important;
                        flex-shrink: 0 !important;
                    }
                    
                    /* Scrollbar Personalizada */
                    .report-card-content::-webkit-scrollbar {
                        width: 6px;
                    }
                    .report-card-content::-webkit-scrollbar-track {
                        background: #f1f1f1;
                        border-radius: 10px;
                    }
                    .report-card-content::-webkit-scrollbar-thumb {
                        background: #888;
                        border-radius: 10px;
                    }
                    .report-card-content::-webkit-scrollbar-thumb:hover {
                        background: #555;
                    }
                }
                
                /* Mobile: Altura automática, sem scroll, SEM largura mínima */
                @media (max-width: 768px) {
                    .report-card-wrapper {
                        height: auto !important;
                        min-width: 0 !important;  /* ✅ Remove largura mínima no mobile */
                    }
                    
                    .report-card-content {
                        overflow: visible !important;
                    }
                    
                    .report-card-buttons {
                        margin-top: 12px !important;
                    }
                }
            </style>
            ''')
            ReportsPage._css_injected = True



        with ui.column().style('width: 100%; max-width: 1200px; gap: 1rem;'):
            with ui.row().style('width: 100%; justify-content: space-between; align-items: center;'):
                ui.label('Relatórios dos Questionários').style(
                    'font-size: 1.4rem; font-weight: 700; color: #111827;')
                with ui.row().style('gap: 0.5rem; align-items: center;'):
                    ui.button(
                        'Exportação Personalizada',
                        on_click=self._go_custom_export,
                        icon='tune',
                    ).props('outline color=primary').style('border-radius: 8px; height: 36px;')
                    if self.on_back:
                        ui.button('Voltar', on_click=self.on_back).props('outline').style(
                            'border-radius: 8px; height: 36px;')







            self.grid_container = ui.column().style('width: 100%;')
            self._load_reports()







    def _load_reports(self):
        self.grid_container.clear()
        creator_id = (session_manager.current_user or {}).get('id')







        if not creator_id:
            with self.grid_container:
                with ui.card().style('padding: 2rem; text-align: center;'):
                    ui.icon('error', size='3rem', color='negative')
                    ui.label('Sessão inválida: usuário não identificado.').style(
                        'color: #b91c1c; font-size: 1.1rem;')
            return







        with self.grid_container:
            with ui.row().style('justify-content: center; margin: 2rem;'):
                ui.spinner(size='2rem', color='primary')
                ui.label('Carregando questionários...').style('margin-left: 1rem;')







        try:
            questionnaires = questionnaire_service.list_by_creator(creator_id) or []
            self.grid_container.clear()







            if not questionnaires:
                with self.grid_container:
                    with ui.card().style('padding: 2rem; text-align: center;'):
                        ui.icon('inbox', size='3rem', color='grey')
                        ui.label('Você ainda não possui questionários.').style(
                            'color: #6b7280; font-size: 1.1rem;')
                return







            with self.grid_container:
                with ui.row().style(
                    'width: 100%; gap: 1rem; flex-wrap: wrap; '
                    'justify-content: flex-start; align-items: stretch;'  
                ):                  
                    for questionnaire in questionnaires:
                        self._render_questionnaire_card(questionnaire)







        except Exception as e:
            self.grid_container.clear()
            with self.grid_container:
                with ui.card().style('padding: 2rem; text-align: center;'):
                    ui.icon('error', size='3rem', color='negative')
                    ui.label(f'Erro ao carregar questionários: {str(e)}').style('color: #b91c1c;')







    def _render_questionnaire_card(self, questionnaire):
        qid = questionnaire.get('id')
        title = questionnaire.get('titulo', 'Sem título')
        description = questionnaire.get('descricao', '')



        with ui.card().classes('report-card-wrapper').style(
            'border-radius: 12px; padding: 1.5rem; '
            'cursor: pointer; transition: transform 0.2s; '
            'max-width: 400px; min-width: 0; '  
            'word-wrap: break-word; overflow-wrap: break-word;'
        ):
            with ui.column().classes('report-card-content').style('gap: 0.75rem; width: 100%; min-width: 0;'):
                with ui.column().style('gap: 0.5rem; width: 100%; min-width: 0;'):
                    with ui.row().style('align-items: flex-start; gap: 0.5rem; width: 100%; min-width: 0;'):
                        ui.icon('quiz', color='primary').style('flex-shrink: 0;')
                        ui.label(title).style(
                            'font-size: 1.1rem; font-weight: 700; color: #111827; '
                            'word-wrap: break-word; overflow-wrap: break-word; word-break: break-word; '
                            'overflow: hidden; text-overflow: ellipsis; display: -webkit-box; '
                            '-webkit-line-clamp: 2; -webkit-box-orient: vertical; '
                            'flex: 1; min-width: 0; max-width: 100%;'
                        )







                    if description:
                        ui.label(description).style(
                            'color: #6b7280; font-size: 0.9rem; line-height: 1.4; '
                            'overflow: hidden; text-overflow: ellipsis; display: -webkit-box; '
                            '-webkit-line-clamp: 2; -webkit-box-orient: vertical; '
                            'word-wrap: break-word; overflow-wrap: break-word; word-break: break-word; '
                            'min-width: 0; max-width: 100%;'
                        )







                self._render_summary_metrics(qid)
            
            with ui.row().classes('report-card-buttons').style('gap: 0.5rem; width: 100%; flex-wrap: wrap; min-width: 0;'):
                ui.button('Relatório', on_click=lambda q=qid: self._view_full_report(q)) \
                    .props('color=primary').style('flex: 1; min-width: 100px; height: 36px;')







                with ui.dropdown_button('', icon='download').props('outline color=green').style(
                    'height: 36px; padding: 0 8px;'
                ).tooltip('Exportar Relatório'):
                    ui.item('Baixar CSV', on_click=lambda q=qid: self._export_format(q, 'csv')).props('icon=file_download')
                    ui.item('Baixar JSON', on_click=lambda q=qid: self._export_format(q, 'json')).props('icon=download')







    def _export_format(self, questionnaire_id, format_type):
        try:
            success = report_service.download_report(questionnaire_id, format_type)
            if success:
                ui.notify(f'Download do {format_type.upper()} iniciado!', type='positive')
            else:
                ui.notify(f'Erro ao iniciar o download {format_type.upper()}', type='negative')
        except Exception as e:
            ui.notify(f'Erro ao exportar {format_type.upper()}: {str(e)}', type='negative')







    def _render_summary_metrics(self, questionnaire_id):
        try:
            summary = report_service.get_summary_report(questionnaire_id)
            if summary:
                with ui.card().style(
                    'padding: 0.75rem; margin: 0; width: 100%; min-width: 0; '
                    'background: #f8fafc; border: 1px solid #e2e8f0;'
                ):
                    ui.label('Resumo').style(
                        'font-size: 0.9rem; font-weight: 600; color: #374151; margin-bottom: 0.5rem;'
                    )







                    with ui.row().style('gap: 0.75rem; width: 100%; justify-content: space-between; flex-wrap: wrap; min-width: 0;'):
                        with ui.column().style('align-items: center; gap: 0.25rem; flex: 1; min-width: 60px;'):
                            ui.label(str(summary.get('total_submissions', 0))).style(
                                'font-size: 1.2rem; font-weight: 700; color: #1f2937;'
                            )
                            ui.label('Respostas').style('font-size: 0.75rem; color: #6b7280; white-space: nowrap;')







                        with ui.column().style('align-items: center; gap: 0.25rem; flex: 1; min-width: 60px;'):
                            ui.label(f"{summary.get('average_score', 0):.1f}").style(
                                'font-size: 1.2rem; font-weight: 700; color: #059669;'
                            )
                            ui.label('Média').style('font-size: 0.75rem; color: #6b7280; white-space: nowrap;')







                        with ui.column().style('align-items: center; gap: 0.25rem; flex: 1; min-width: 60px;'):
                            ui.label(str(summary.get('max_score', 0))).style(
                                'font-size: 1.2rem; font-weight: 700; color: #dc2626;'
                            )
                            ui.label('Máxima').style('font-size: 0.75rem; color: #6b7280; white-space: nowrap;')







                        with ui.column().style('align-items: center; gap: 0.25rem; flex: 1; min-width: 60px;'):
                            ui.label(str(summary.get('min_score', 0))).style(
                                'font-size: 1.2rem; font-weight: 700; color: #f59e0b;'
                            )
                            ui.label('Mínima').style('font-size: 0.75rem; color: #6b7280; white-space: nowrap;')
            else:
                with ui.card().style(
                    'padding: 0.75rem; background: #fef3cd; border: 1px solid #fbbf24; width: 100%;'):
                    ui.label('Nenhum dado disponível').style(
                        'font-size: 0.9rem; color: #92400e; text-align: center;')
        except Exception:
            with ui.card().style(
                'padding: 0.75rem; background: #fee2e2; border: 1px solid #fca5a5; width: 100%;'):
                ui.label('Erro ao carregar resumo').style(
                    'font-size: 0.9rem; color: #dc2626; text-align: center;')








    def _view_full_report(self, questionnaire_id):
        def render_report():
            QuestionnaireDetailedReport(
                questionnaire_id,
                container=self.content_container,
                on_back=self._back_to_reports
            ).render()







        router.clear_and_render(self.content_container, render_report)







    def _view_analytics(self, questionnaire_id):
        def render_analytics():
            QuestionnaireAnalyticsReport(
                questionnaire_id,
                container=self.content_container,
                on_back=self._back_to_reports
            ).render()







        router.clear_and_render(self.content_container, render_analytics)






    def _go_custom_export(self):
        def render_export():
            CustomExportPage(
                on_back=self._back_to_reports,
                content_container=self.content_container,
            ).render()
        router.clear_and_render(self.content_container, render_export)

    def _back_to_reports(self):
        router.clear_and_render(self.content_container, self.render)
