from nicegui import ui
from components.auth.login_form import LoginForm
from components.auth.signup_form import SignupForm
from utils.session_manager import session_manager


class AuthModal:
    def __init__(self, on_success_callback=None):
        self.on_success_callback = on_success_callback
        self.dialog = None
        self.current_form = 'login'  

    def show(self):
        """Mostra o modal de autenticação"""
        if self.dialog:
            self.dialog.close()

        self.dialog = ui.dialog()

        with self.dialog:
            with ui.card().style('width: 400px; padding: 2rem;'):
                with ui.column().style('width: 100%; gap: 1rem;'):
                    self.form_container = ui.column().style('width: 100%;')
                    self._render_current_form()

        self.dialog.open()

    def _render_current_form(self):
        """Renderiza o formulário atual"""
        self.form_container.clear()

        with self.form_container:
            if self.current_form == 'login':
                ui.label('Fazer Login').style('font-size: 1.5rem; font-weight: 700; text-align: center;')
                ui.label('Você precisa estar logado para responder este questionário').style(
                    'color: #6b7280; text-align: center; margin-bottom: 1rem;'
                )

                login_form = LoginForm(
                    on_success_callback=self._on_auth_success,
                    on_switch_to_signup=self._switch_to_signup
                )
                login_form.render()

            else:  
                ui.label('Criar Conta').style('font-size: 1.5rem; font-weight: 700; text-align: center;')
                ui.label('Crie uma conta para responder questionários').style(
                    'color: #6b7280; text-align: center; margin-bottom: 1rem;'
                )

                signup_form = SignupForm(
                    on_success_callback=self._on_auth_success,
                    on_switch_to_login=self._switch_to_login
                )
                signup_form.render()

    def _switch_to_signup(self):
        """Muda para formulário de cadastro"""
        self.current_form = 'signup'
        self._render_current_form()

    def _switch_to_login(self):
        """Muda para formulário de login"""
        self.current_form = 'login'
        self._render_current_form()

    def _on_auth_success(self):
        """Callback de sucesso na autenticação"""
        if self.dialog:
            self.dialog.close()

        if self.on_success_callback:
            self.on_success_callback()

    def close(self):
        """Fecha o modal"""
        if self.dialog:
            self.dialog.close()
