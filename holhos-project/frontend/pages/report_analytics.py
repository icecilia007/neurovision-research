from nicegui import ui
from services.report_service import report_service


class QuestionnaireAnalyticsReport:
    def __init__(self, questionnaire_id, container=None, on_back=None):
        self.questionnaire_id = questionnaire_id
        self.container = container
        self.on_back = on_back

    def render(self):
        target = self.container or ui.column().style('width: 100%;')
        with target:
            with ui.row().style('width: 100%; justify-content: space-between; align-items: center;'):
                ui.label('Analytics Avançados').style(
                    'font-size: 1.4rem; font-weight: 700; color: #111827;')
                ui.button('Voltar', on_click=self.on_back).props('outline')

            self._load_analytics(target)

    def _load_analytics(self, target):
        loading_container = ui.column()
        with loading_container:
            with ui.row().style('justify-content: center; margin: 2rem;'):
                ui.spinner(size='2rem')
                ui.label('Carregando analytics...')

        try:
            analytics = report_service.get_analytics(self.questionnaire_id)
            loading_container.clear()
            with target:
                self._render_analytics(analytics)
        except Exception as e:
            loading_container.clear()
            with target:
                with ui.card().style('padding: 2rem; text-align: center;'):
                    ui.icon('error', size='3rem', color='negative')
                    ui.label(f'Erro: {str(e)}').style('color: #b91c1c;')

    def _render_analytics(self, analytics):
        score_dist = analytics.get('score_distribution', {})
        top_performers = analytics.get('top_performers', [])
        difficult_questions = analytics.get('difficult_questions', [])

        with ui.card().style('width: 100%; padding: 1.5rem; margin-bottom: 1rem;'):
            ui.label('Distribuição de Pontuações').style('font-size: 1.3rem; font-weight: 700; margin-bottom: 1rem;')

            with ui.row().style('gap: 1rem; flex-wrap: wrap; justify-content: center;'):
                for key, value in score_dist.items():
                    if key in ['min', 'max', 'mean', 'median']:
                        with ui.card().style(
                                'padding: 1rem; min-width: 120px; max-width: 160px; text-align: center; flex: 1;'):
                            ui.label(key.title()).style('font-size: 0.9rem; color: #6b7280;')
                            ui.label(f"{value:.1f}").style('font-size: 1.5rem; font-weight: 700; color: #111827;')

        if top_performers:
            with ui.card().style('width: 100%; padding: 1.5rem; margin-bottom: 1rem;'):
                ui.label('Melhores Resultados').style('font-size: 1.3rem; font-weight: 700; margin-bottom: 1rem;')

                for i, performer in enumerate(top_performers, 1):
                    with ui.row().style('align-items: center; padding: 0.5rem 0; border-bottom: 1px solid #e5e7eb;'):
                        ui.label(f"#{i}").style('width: 30px; font-weight: 600; color: #6b7280;')
                        ui.label(performer.get('name', '')).style('flex: 1; font-weight: 600;')
                        ui.label(f"{performer.get('score', 0):.1f}").style('color: #059669; font-weight: 700;')

        if difficult_questions:
            with ui.card().style('width: 100%; padding: 1.5rem;'):
                ui.label('Perguntas Mais Difíceis').style('font-size: 1.3rem; font-weight: 700; margin-bottom: 1rem;')

                for question in difficult_questions:
                    with ui.card().style('margin-bottom: 0.5rem; padding: 1rem; background: #fef2f2;'):
                        ui.label(question.get('question_text', '')).style(
                            'font-weight: 600; color: #111827; margin-bottom: 0.5rem;')
                        ui.label(f"Taxa de acerto: {question.get('accuracy_percentage', 0):.1f}%").style(
                            'color: #dc2626;')
