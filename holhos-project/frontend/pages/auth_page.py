from nicegui import ui
from components.auth.login_form import LoginForm
from components.auth.signup_form import SignupForm

class AuthPage:
    def __init__(self, on_login_success=None, on_switch_to_signup=None, force_signup: bool = False):
        self.on_login_success = on_login_success
        self.on_switch_to_signup = on_switch_to_signup
        self.force_signup = force_signup

    def render(self):
        with ui.column().style('width: 100%; max-width: 420px; align-items: stretch;'):
            with ui.card().style('width: 100%; padding: 1.5rem; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.08);'):
                title = 'Cadastro' if self.force_signup else 'Login'
                ui.label(title).style('font-size: 1.4rem; font-weight: 700; color: #111827; text-align: center; margin-bottom: 0.75rem;')

                if self.force_signup:
                    SignupForm(
                        on_success_callback=self.on_login_success,
                        on_switch_to_login=self.on_login_success
                    ).render()
                else:
                    LoginForm(
                        on_success_callback=self.on_login_success,
                        on_switch_to_signup=(self.on_switch_to_signup if self.on_switch_to_signup else lambda: None)
                    ).render()
