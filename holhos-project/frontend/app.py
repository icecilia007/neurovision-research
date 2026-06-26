from nicegui import ui, app
from pages.auth_page import AuthPage
from pages.dashboard import DashboardPage
from utils.session_manager import session_manager
from config import config
import router

@ui.page('/')
def main_page():
    with ui.header().style('background: #1f2937; color: white; padding: 0.75rem 1.5rem;'):
        ui.label('Sistema de Questionários').style('font-size: 1.1rem; font-weight: 600;')

    content = ui.column().style('min-height: calc(100vh - 120px); width: 100%; align-items: center; justify-content: flex-start; padding: 1.5rem 1rem;')

    with ui.footer().style('background: #f3f4f6; color: #4b5563; padding: 0.5rem 1rem;'):
        ui.label('© 2025 - Projeto Questionários')

    def _clear_content():
        content.clear()

    def render_login():
        _clear_content()
        with content:
            AuthPage(on_login_success=render_dashboard, on_switch_to_signup=render_signup).render()

    def render_signup():
        _clear_content()
        with content:
            AuthPage(on_login_success=render_login, on_switch_to_signup=None, force_signup=True).render()

    def render_dashboard():
        _clear_content()
        with content:
            DashboardPage(on_logout=render_login, content_container=content).render()

    if session_manager.is_authenticated:
        render_dashboard()
    else:
        render_login()

if __name__ in {'__main__', '__mp_main__'}:
    ui.run(
        host='0.0.0.0',
        port=8080,
        title='Sistema de Questionários',
        favicon='👁️',
        reload=True,
        show=False,
        storage_secret=config.STORAGE_SECRET,
        proxy_headers=True,
        forwarded_allow_ips='*'
    )
