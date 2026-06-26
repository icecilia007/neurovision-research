from nicegui import ui, app
from utils.session_manager import session_manager
from pages.questionnaire_list_page import QuestionnaireListPage
from pages.reports_page import ReportsPage
import router

CARD = 'width: 100%; border-radius: 12px;'

class DashboardPage:
    def __init__(self, on_logout=None, content_container=None):
        self.on_logout = on_logout
        self.content_container = content_container

    def render(self):
        name = (session_manager.current_user or {}).get('nome_completo', 'Usuário')

        with ui.column().style('width: 100%; max-width: 1200px; gap: 1rem;'):
            with ui.row().style('width: 100%; justify-content: space-between; align-items: center;'):
                ui.label(f'Bem-vindo, {name}!').style('font-size: 1.4rem; font-weight: 700; color: #111827;')
                ui.button('Logout', on_click=self._logout).props('outline color=negative').style('border-radius: 8px; height: 36px;')

            ui.separator()

            with ui.row().style('gap: 1.5rem; width: 100%; justify-content: center; flex-wrap: wrap;'):
                self._card('quiz', 'Questionários', 'Gerencie seus questionários', self._go_list)
                self._card('analytics', 'Relatórios', 'Visualize métricas e análises', self._go_reports)

    def _card(self, icon: str, title: str, subtitle: str, action):
        with ui.card().style(CARD + ' padding: 1.5rem; cursor: pointer; transition: all 0.2s; flex: 1; min-width: 300px; max-width: 400px; display: flex; justify-content: center;'):
            with ui.column().style('width: 100%; align-items: center; gap: 1rem;'):
                ui.icon(icon, size='3rem', color='primary')
                ui.label(title).style('font-size: 1.2rem; font-weight: 700; color: #111827; text-align: center;')
                ui.label(subtitle).style('color: #6b7280; text-align: center; margin-bottom: 1rem;')
                ui.button('Acessar', on_click=action).props('color=primary').style('border-radius: 8px; width: 120px;')

    def _go_list(self):
        def render_list():
            QuestionnaireListPage(on_back=self._back_to_dashboard, content_container=self.content_container).render()
        router.clear_and_render(self.content_container, render_list)

    def _go_reports(self):
        def render_reports():
            ReportsPage(on_back=self._back_to_dashboard, content_container=self.content_container).render()
        router.clear_and_render(self.content_container, render_reports)

    def _back_to_dashboard(self):
        router.clear_and_render(self.content_container, self.render)

    def _logout(self):
        session_manager.logout()
        if self.on_logout:
            self.on_logout()
