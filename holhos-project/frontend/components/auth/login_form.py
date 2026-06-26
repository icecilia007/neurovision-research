from nicegui import ui
from services.user_service import user_service
from utils.validators import validators
from utils.session_manager import session_manager

BTN_FULL = 'width: 100%; height: 40px; border-radius: 8px;'
INPUT_STYLE = 'width: 100%;'

class LoginForm:
    def __init__(self, on_success_callback=None, on_switch_to_signup=None):
        self.on_success_callback = on_success_callback
        self.on_switch_to_signup = on_switch_to_signup

        self.email_input = None
        self.password_input = None
        self.error_label = None

    def render(self):
        with ui.column().style('width: 100%; gap: 0.75rem;'):
            self.email_input = ui.input(label='Email', placeholder='seu@email.com').style(INPUT_STYLE)
            self.password_input = ui.input(label='Senha', password=True, placeholder='••••••').style(INPUT_STYLE)

            ui.button('Entrar', on_click=self._on_login, color='primary').style(BTN_FULL)

            self.error_label = ui.label('').style('color: #b91c1c; text-align: center; min-height: 20px;')

            ui.separator()

            with ui.row().style('width: 100%; justify-content: center;'):
                ui.button('Criar conta', on_click=(lambda: self.on_switch_to_signup() if self.on_switch_to_signup else None))\
                  .props('outline color=primary').style(BTN_FULL)

    def _on_login(self):
        self.error_label.text = ''
        email = (self.email_input.value or '').strip()
        password = (self.password_input.value or '')

        ok_email, email_err = validators.validate_email(email)
        if not ok_email:
            self.error_label.text = email_err
            return

        ok_pwd, pwd_err = validators.validate_password(password)
        if not ok_pwd:
            self.error_label.text = pwd_err
            return

        try:
            user = user_service.authenticate_user(email, password)
        except Exception as e:
            error_message = str(e)
            self.error_label.text = error_message
            ui.notify(error_message, type='negative')
            return

        if user:
            session_manager.login(user)
            ui.notify(f'Bem-vindo, {user["nome_completo"]}!', type='positive')
            if self.on_success_callback:
                self.on_success_callback()
        else:
            self.error_label.text = 'Email ou senha inválidos'
